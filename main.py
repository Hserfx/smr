import argparse
import os
from dotenv import load_dotenv
import requests
import json
import logging
import time
from datetime import datetime, date, timedelta
from collections import defaultdict


def open_file_with_directory(file_path, mode='w'):
    folder_path = os.path.dirname(file_path)
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    return open(file_path, mode)


# GET ACCESS TOKEN TO GOPOS
def get_token(url, creds, **kwargs):
    logger.info('sending token request...')
    r = requests.get(url, params=creds, **kwargs)

    if r.status_code == 200:
        logger.info('token granted')
        return r.json()['access_token']
    else:
        logger.info(f'token access denied with status code {r.status_code}')
        return

# GET ORDERS INFO BY DATE
def get_orders(id, headers):
    logging.info('sending request to get orders')
    page = 0
    orders = []
    invoices = []
    while 1:
        params = {
            'status' : 'CLOSED',
            'updated_at_from' : (day + timedelta(hours=3)).isoformat(),
            'updated_at_to' : (day + timedelta(days=21) + timedelta(hours=27)).isoformat(),
            'size' : 100,
            'page' : page,
            'sort' : 'id, asc',
            'include' : ['tax_items', 'transactions', 'custom_fields', 'employee']
        }

        for i in range(6):
            if i == 5:
                logger.info(f'request denied with status code {r.status_code} after {i} tries')
                return
            r = requests.get(f'https://app.gopos.io/api/v3/{id}/orders', headers=headers, params=params)
            if r.status_code != 200:
                logger.info(f'request denied with status code {r.status_code} try: {i}')
                time.sleep(10)
                continue
            else:
                break
        
        if not r.json()['data']:
            return (orders, invoices)

        for order in r.json()['data']:
            if day + timedelta(hours=3) > datetime.fromisoformat(order['created_at']) or datetime.fromisoformat(order['created_at']) >= day + timedelta(hours=27):
                continue
            
            if 'tax_id_no' in order.keys():
                invoices.append(order)
            else:
                orders.append(order)

        page+=1

def get_invoice(id, invoice_no, headers):
    logging.info('sending request to get invoices data')
    invoices = []
    params = {
        'updated_at_from' : (day + timedelta(hours=4)).isoformat(),
        'updated_at_to' : (day + timedelta(hours=28)).isoformat(),
        'size' : 50,
        'status': 'CONFIRMED',
        'order_number' : invoice_no,
        'include' : ['taxes', 'payments']
    }
    for i in range(6):
        if i == 5:
            logger.info(f'request denied with status code {r.status_code} after {i} tries')
            return
        r = requests.get(f'https://app.gopos.io/api/v3/{id}/invoices', headers=headers, params=params)
        if r.status_code != 200:
            logger.info(f'request denied with status code {r.status_code} try: {i}')
            time.sleep(10)
            continue
        else:
            break
    
    if not r.json()['data']:
        return None
    else:
        return r.json()['data'][0]

# ASSIGN CASH/STAFFORDER TO EMPLOYEE
def assign_employee(orders):
    employees = {}
    for order in orders:
        if 'tax_id_no' in order.keys():
            continue
        employees[order['employee']['name']] = round(employees.setdefault(order['employee']['name'], 0) + order['total_price']['amount'], 2)

    return employees

# COUNT TAXES FOR NORMAL ORDERS (NOT INVOICES)
def count_taxes(orders, payment_method):
    taxes = {}
    for order in orders:
        if len(order['transactions']) > 1:
            for transaction in order['transactions']:
                if transaction['payment_method_name'] == 'Gotówka':
                    if payment_method == 'Gotowka':
                        netto = round(transaction['price']['amount']/108*100,2)
                        vat = transaction['price']['amount'] - netto
                        if not 8 in taxes:
                            taxes[8] = {}
                        taxes[8]['net'] = taxes[8].setdefault('net', 0) + netto
                        taxes[8]['tax'] = taxes[8].setdefault('tax', 0) + vat
                        taxes[8]['brt'] = taxes[8].setdefault('brt', 0) + transaction['price']['amount']
                    else:
                        netto = round(transaction['price']['amount']/108*100,2)
                        vat = transaction['price']['amount'] - netto
                        if not 8 in taxes:
                            taxes[8] = {}
                        taxes[8]['net'] = taxes[8].setdefault('net', 0) - netto
                        taxes[8]['tax'] = taxes[8].setdefault('tax', 0) - vat
                        taxes[8]['brt'] = taxes[8].setdefault('brt', 0) - transaction['price']['amount']
                        for tax in order['tax_items']:
                            if not tax['tax_amount'] in taxes:
                                taxes[tax['tax_amount']] = {}
                            taxes[tax['tax_amount']]['net'] = round(taxes[tax['tax_amount']].setdefault('net', 0) + tax['total_price_net']['amount'], 2)
                            taxes[tax['tax_amount']]['tax'] = round(taxes[tax['tax_amount']].setdefault('tax', 0) + tax['total_price_tax']['amount'], 2)
                            taxes[tax['tax_amount']]['brt'] = round(taxes[tax['tax_amount']].setdefault('brt', 0) + tax['total_price_gross']['amount'], 2)
                else:
                    continue
            continue
        for tax in order['tax_items']:
            if not tax['tax_amount'] in taxes:
                taxes[tax['tax_amount']] = {}
            taxes[tax['tax_amount']]['net'] = round(taxes[tax['tax_amount']].setdefault('net', 0) + tax['total_price_net']['amount'], 2)
            taxes[tax['tax_amount']]['tax'] = round(taxes[tax['tax_amount']].setdefault('tax', 0) + tax['total_price_tax']['amount'], 2)
            taxes[tax['tax_amount']]['brt'] = round(taxes[tax['tax_amount']].setdefault('brt', 0) + tax['total_price_gross']['amount'], 2)
    
    return dict(sorted(taxes.items()))



# COUNT TAXES FOR INVOICE WITH RECEIPT
def count_invoice_receipt_taxes(invoice_receipt):
    taxes = {}
    for tax in invoice_receipt['tax_items']:
        taxes[tax['tax_amount']] = {}
        taxes[tax['tax_amount']]['net'] = tax['total_price_net']['amount']
        taxes[tax['tax_amount']]['tax'] = tax['total_price_tax']['amount']
        taxes[tax['tax_amount']]['brt'] = tax['total_price_gross']['amount']
    
    return dict(sorted(taxes.items()))

# COUNT TAXES FOR INVOICE
def count_invoice_taxes(invoice):
    taxes = {}

    for tax in invoice['taxes']:
        taxes[tax['tax_rate']] = {}
        taxes[tax['tax_rate']]['net'] = tax['price_net']['amount']
        taxes[tax['tax_rate']]['tax'] = tax['price_tax']['amount']
        taxes[tax['tax_rate']]['brt'] = tax['price_gross']['amount']


    return dict(sorted(taxes.items()))

def invoice_report(order, prefix):
        
    payment_methods = {
        1 : 'Gotówka',
        2 : 'Karta',
        3 : 'Przelew'
    }
    taxes = count_invoice_taxes(order)
    out = ''
    out += f'"KON";"{order['recipient']['tax_id_no']}";"{order['recipient']['tax_id_no']}";"{order['recipient']['name']}";0;0;"{order['recipient']['address']['street']} \
{order['recipient']['address']['build_nr']}";"{order['recipient']['address']['zip_code']}";"{order['recipient']['address']['city']}";"{order['recipient']['address']['country']}"\n\
"FS";"SPR";{order['issued_at']};"{order['number']}";"{order['recipient']['tax_id_no']}";"";{order['price_sum_gross']['amount']:.2f};{order['sold_at']};{order['payments'][0]['paid_at']};\
"{order.get('comment', '')}";"";;1;"";"PLN"\n'
    
    for vat in taxes:
        out += f'"VAT";{int(float(vat))};0;{taxes[vat]['net']:.2f};{taxes[vat]['tax']:.2f};{taxes[vat]['brt']:.2f};5;0;"";;0\n'
    
    out += f'"PLA";"{order['recipient']['tax_id_no']}";{payment_methods[order['payments'][0]['payment_method_id']]};{order['payment_due_date']};\
{order['price_sum_gross']['amount']:.2f};;""\n'
    return out
    
def invoice_receipt_report(order, prefix):
    taxes = count_invoice_receipt_taxes(order)
    issued_at = f'{datetime.fromisoformat(order['created_at']):%Y-%m-%d}'
    out = ''
    out += f'"KON";"{order['tax_id_no']}";"{order['tax_id_no']}";"WyszukajKontrahenta";0;0;"";"";"";""\n\
"FS";"FP";{issued_at};"{order['number']}";"{order['tax_id_no']}";"";{order['total_price']['amount']:.2f};{issued_at};{issued_at}\n'
    
    for vat in taxes:
        out += f'"VAT";{int(float(vat))};0;{taxes[vat]['net']:.2f};{taxes[vat]['tax']:.2f};{taxes[vat]['brt']:.2f};5;0;"";;0\n'

    out += f'"PLA";"{order['tax_id_no']}";"{order['transactions'][0]['payment_method_name']}";{issued_at};{order['total_price']['amount']:.2f};;""\n'
    return out

def check_report(orders, prefix):
    if not orders:
        return ''
    taxes = count_taxes(orders, 'Karta')
    total = f'{sum([item['brt'] for _, item in taxes.items()]):.2f}'
    day_short = f'{datetime.fromisoformat(datetime.isoformat(day)):%Y-%m-%d}'

    out = ''
    out += f'"KON";"Detal";"";"Odbiorca detaliczny";0;1;"";"";"";""\n\
"FS";"SPAR";{day_short};"{prefix}K-{day_short}";"Detal";"";{total};{day_short};{day_short}\n'
    
    for vat in taxes:
        out += f'"VAT";{int(float(vat))};0;{taxes[vat]['net']:.2f};{taxes[vat]['tax']:.2f};{taxes[vat]['brt']:.2f}\n'

    out += f'"PLA";"Detal";"Karta";{day_short};{total};;""\n\
"PRV";"GrupaTowarowaVAT";"01"\n'
    return out

def cash_report(orders, prefix):
    if not orders:
        return ''
    employees = assign_employee(orders)
    taxes = count_taxes(orders, 'Gotowka')
    total = f'{sum([item['brt'] for _, item in taxes.items()]):.2f}'
    day_short = f'{datetime.fromisoformat(datetime.isoformat(day)):%Y-%m-%d}'

    out = ''
    out += f'"KON";"Detal";"";"Odbiorca detaliczny";0;1;"";"";"";""\n\
"FS";"SPAR";{day_short};"{prefix}G-{day_short}";"Detal";"";{total};{day_short};{day_short}\n'
    
    for vat in taxes:
        out += f'"VAT";{int(float(vat))};0;{taxes[vat]['net']:.2f};{taxes[vat]['tax']:.2f};{taxes[vat]['brt']:.2f}\n'

    out += f'"PLA";"Detal";"Gotówka";{day_short};{total};;""\n'
    for employee, value in employees.items():
        out += f'"POZ";"{employee}";{value:.2f};"";"";"Usługi"\n'
    out += f'"PRV";"GrupaTowarowaVAT";"01"\n'
    return out

def delivery_report(orders, prefix):
    if not orders:
        return ''
    taxes = count_taxes(orders, 'delivery')
    total = f'{sum([item['brt'] for _, item in taxes.items()]):.2f}'
    day_short = f'{datetime.fromisoformat(datetime.isoformat(day)):%Y-%m-%d}'

    out = ''
    out += f'"KON";"Detal";"";"Odbiorca detaliczny";0;1;"";"";"";""\n\
"FS";"SPAR";{day_short};"{prefix}D-{day_short}";"Detal";"";{total};{day_short};{day_short}\n'
    
    for vat in taxes:
        out += f'"VAT";{int(float(vat))};0;{taxes[vat]['net']:.2f};{taxes[vat]['tax']:.2f};{taxes[vat]['brt']:.2f}\n'

    out += f'"PLA";"Detal";"Dowóz";{day_short};{total};;""\n'
    return out

def staff_report(orders, prefix):
    if not orders:
        return ''
    employees = assign_employee(orders)
    taxes = count_taxes(orders, 'staff')
    total = f'{sum([item['brt'] for _, item in taxes.items()]):.2f}'
    day_short = f'{datetime.fromisoformat(datetime.isoformat(day)):%Y-%m-%d}'

    out = ''
    out += f'"KON";"Detal";"";"Odbiorca detaliczny";0;1;"";"";"";""\n\
"FS";"SPARPRAC";{day_short};"{prefix}P-{day_short}";"Detal";"";{total};{day_short};{day_short}\n'
    
    for vat in taxes:
        out += f'"VAT";{int(float(vat))};0;{taxes[vat]['net']:.2f};{taxes[vat]['tax']:.2f};{taxes[vat]['brt']:.2f}\n'

    out += f'"PLA";"Detal";"Przelew";{day_short};{total};;""\n'
    for employee, value in employees.items():
        out += f'"POZ";"{employee}";{value:.2f};"";"";"Usługi"\n'
    return out

def create_report(payments, path, prefix):
    with open_file_with_directory(path, 'w+') as file:
        file.write(f'"ODD";"Losteria01"\n')
        for order in payments['invoices']:
            file.write(invoice_report(order, prefix))
        for order in payments['receipt_invoices']:
            file.write(invoice_receipt_report(order, prefix))
        file.write(check_report(payments['check'], prefix))
        file.write(cash_report(payments['cash'], prefix))
        file.write(delivery_report(payments['delivery'], prefix))
        file.write(staff_report(payments['staff'], prefix))


def main():
    # CREDS CONFIGURATION
    load_dotenv()
    clientID = os.getenv('clientID')
    clientSecret = os.getenv('clientSecret')
    email = os.getenv('email')
    pwd = os.getenv('pwd')
    
    creds = {
        'client_id' : clientID,
        'client_secret' : clientSecret,
        'grant_type' : 'password',
        'username' : email,
        'password' : pwd
    }


    url = 'https://app.gopos.io/oauth/token'
    
    # 5 retries of getting token else exit
    for i in range(0,6):
        token = get_token(url, creds)

        if not token and i!=5:
            logger.info(f'{i+1} retry to get access token')
            time.sleep(300.0)
            continue
        elif not token and i==5:
            logger.info('Couldn\'t get access token after 5 tries, program shutdowning')
            return

        break
    

    headers = {
        'Authorization' : f'Bearer {token}'
    }
    logger.info('sending request to get ids')

    r = requests.get(url='https://app.gopos.io/api/v3/me', headers=headers)

    if r.status_code != 200:
        logger.info(f'request denied with status code {r.status_code}')
        return

    
    localisations = sorted(r.json()['data'], key=lambda x: x['id'])
    logger.info('organizations data acquired')
    # GET REPORTS OF EVERY LOCALISATION IN ORGANIZATIONS
    for localisation, prefix in zip(localisations, ['', 'P']):
        id, name = localisation['id'], localisation['name']

        if args.loc:
            if name != args.loc:
                print(args.loc)
                continue

        orders, all_invoices = get_orders(id, headers)
        if not orders and not all_invoices:
            logger.info('No orders nor invoices')
            return
        payments = {
            'invoices' : [],
            'receipt_invoices' : [],
            'double' : [],
            'check' : [],
            'cash' : [],
            'delivery' : [],
            'staff' : [],
            'goorder' : []
        }

        # SORT INVOICES TO RECEIPT AND NORMAL
        for invoice in all_invoices:
            invo_details = get_invoice(id, invoice['number'], headers)
            if invo_details:
                payments['invoices'].append(invo_details)
            else:
                payments['receipt_invoices'].append(invoice)

        # SORT ORDERS BY PAYMENT TYPE
        for order in [*orders, *payments['receipt_invoices']]:
            if 'GoOrder' in order['reference_id']:
                payments['delivery'].append(order)
                logging.info(f'order {order['id']} added to delivery')
            elif 'GLOVO' in order['reference_id'] and order['transactions'][0]['payment_method_name'] == 'Przelew':
                payments['delivery'].append(order)
                logging.info(f'order {order['id']} added to delivery')
            elif order['type'] == 'DELIVERY':
                payments['delivery'].append(order)
                logging.info(f'order {order['id']} added to delivery')
            elif len(order['transactions']) > 1:
                payments['check'].append(order)
                payments['cash'].append(order)
                logging.info(f'order {order['id']} added to double')
            else:
                for transaction in order['transactions']:
                    if transaction['payment_method_name'] == 'Karta':
                        payments['check'].append(order)
                        logging.info(f'order {order['id']} added to card')
                    elif transaction['payment_method_name'] == 'Gotówka':
                        payments['cash'].append(order)
                        logging.info(f'order {order['id']} added to cash')
                    elif transaction['payment_method_name'] == 'Przelew STAFF':
                        payments['staff'].append(order)
                        logging.info(f'order {order['id']} added to staff')
                    # RECEIPT WITH TRANSFER APPENDS TO TOTAL PRZELEW STAFF AMOUNT
                    elif order in payments['receipt_invoices'] and transaction['payment_method_name'] == 'Przelew':
                        payments['staff'].append(order)
                        logging.info(f'order {order['id']} added to staff')
                    else:
                        print(order['id'], given_date)
                        logging.info(f'order {json.dumps(order)} not sorted to any payment')

        create_report(payments, f'C:/ImportyKsiegowe/{name}-{given_date}-enovaTxt.txt', prefix)
        # SLEEP TO PREVENT TOO MANY REQUESTS
        time.sleep(5)


if __name__ == '__main__':
       
    yesterday = date.today() - timedelta(hours=24)

    logger = logging.getLogger(__name__)
    logging.basicConfig(format='%(asctime)-8s %(message)s', filename=f'logs/{date.today().isoformat()}.log', level=logging.INFO)

    parser = argparse.ArgumentParser(description='Wybierz date oraz lokalizacje dla ktorej raport ma zostac wygenerowany')
    parser.add_argument(
        '--date',
        default=yesterday,
        help='Wybierz dla jakiej daty ma zostac wygenerowany raport'
    )

    parser.add_argument(
        '--loc',
        default=None,
        help='Wybierz lokalizacje dla ktorej ma zostac wygenerowany raport'
    )
    args = parser.parse_args()

    if args.date:
        given_date = args.date
    else:
        given_date = yesterday

    day = datetime.fromisoformat(f'{given_date}T00:00:00')
    print(given_date)
    logger.info(f'generating reports for day {given_date}')
    main()