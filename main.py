from dotenv import load_dotenv
import os
import requests
import json
import logging
import time
from datetime import datetime, date, timedelta



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
    while 1:
        params = {
            'status' : 'CLOSED',
            'date_from' : (day + timedelta(hours=5)).isoformat(),
            'date_to' : (day + timedelta(hours=28)).isoformat(),
            'size' : 100,
            'page' : page,
            'sort' : 'closed_at, asc',
            'include' : ['tax_items', 'transactions', 'custom_fields', 'employee']
        }

        r = requests.get(f'https://app.gopos.io/api/v3/{id}/orders', headers=headers, params=params)

        if r.status_code != 200:
            logger.info('request denied with status code {r.status_code}')
            return
        
        if not r.json()['data']:
            return orders

        for order in r.json()['data']:
            
            if datetime.fromisoformat(order['created_at']) < day:
                continue
            
            if 'tax_id_no' in order.keys():
                continue
            else:
                orders.append(order)

        page+=1

def get_invoice_data(id, invoice_id, headers):
    logging.info('sending request to get invoice data')

    params = {
        'id' : invoice_id
    }

    r = requests.get(f'https://app.gopos.io/api/v3/{id}/invoices', params=params, headers=headers)

    if r.status_code != 200:
        logging.info('couldn\'t fetch invoice data')
        return
    
    print(r.json())

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

    
    localisations = r.json()['data']
    logger.info('organizations data acquired')

    # GET REPORTS OF EVERY LOCALISATION IN ORGANIZATIONS
    for localisation in localisations:
        id, name = localisation['id'], localisation['name']

        orders = get_orders(id, headers)
        # SORT ORDERS BY PAYMENT TYPE

        check = []
        cash = []
        transfer = []
        delivery = []
        staff = []

        
        for order in orders:

            if order['type'] == 'DELIVERY':
                delivery.append(order)
            elif 'GLOVO' in order['reference_id'] and order['type'] == 'PICK_UP':
                delivery.append(order)
            elif order['transactions'][0]['payment_method_name'] == 'Przelew':
                print(order)
            

            elif order['type'] == 'DINE_IN':
                for transaction in order['transactions']:
                    if transaction['payment_method_name'] == 'Karta':
                        check.append(order)
                    elif transaction['payment_method_name'] == 'Gotówka':
                        cash.append(order)
                    elif transaction['payment_method_name'] == 'Przelew':
                        print(order)
                        transfer.append(order)
        
        
                
                
                



if __name__ == '__main__':
    # LOGGER CONFIGURATION
    for i in range(1, 20):
        given_date = f'2024-10-{str(i).zfill(2)}'
        day = datetime.fromisoformat(f'{given_date}T00:00:00')
        today = date.today()
        logger = logging.getLogger(__name__)
        logging.basicConfig(format='%(asctime)-8s %(message)s', filename=f'logs/{today.isoformat()}.log', level=logging.INFO)
        logger.info('app started')

        main()