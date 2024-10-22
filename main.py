from dotenv import load_dotenv
import os


if __name__ == '__main__':
    load_dotenv()
    clientID = os.getenv('clientID')
    clientSecret = os.getenv('clientSecret')
    email = os.getenv('email')
    pwd = os.getenv('pwd')

    print(pwd)