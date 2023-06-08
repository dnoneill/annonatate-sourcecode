# Annonatate

## Running Locally
1. Download code
2. Create OAuth App (https://docs.github.com/en/developers/apps/building-oauth-apps/creating-an-oauth-app)
    - Make sure to set the callback url to http://127.0.0.1:5000/authorize or http://0.0.0.0:5000/authorize
3. Copy the .env.template file to .env
4. Fill out the variables with your OAuth client id and secret
5. Install requirements
    ```pip install -r requirements.txt```
6. Run the application 
    ```python wsgi.py```
7. Go to the application in the browser. Make sure the URL you use matches what you put in the callback URL (If you choose http://0.0.0.0:5000/authorize) then make sure to go to http://0.0.0.0:5000 in the browser. 

## Running tests

1. python -m unittest