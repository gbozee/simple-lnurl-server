### LNURL Server for Phoenixd

To start the server run the following commands

```
pip install -r requirements.txt
```

set the following environment variables

```
export LN_ADDRESS_DOMAIN=orange-candles-shine.loca.lt # domain to expose the lnurl address
export LN_USERNAME=phoenixd # the lnurl username you plan on using
export NODE_API_KEY=1234567890 # the http password exposed by phoenixd
export NODE_BASE_URL=http://localhost:3001 # the http url exposed by phoenixd
```

And start the server

```
uvicorn src.app:app
```