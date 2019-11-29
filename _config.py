# -*- coding: utf-8 -*-
import os

TWITTER_ACCOUNT_IDS = { "@mcdonaldsindia":"918869826",
                        "@KFC_India":"112376689",
                        "@dominos_india":"98560085",
                        "@PizzaHutIN":"1635310159",
                        "@burgerkingindia":"2516998464",
                        "@Rajdhani_Thali":"599852134",
                        "@StarbucksIndia":"930270762",
                        "@tacobellindia":"122008951",
                        "@ZomatoIN":"3282245130",
                        "@swiggy_in":"2639625036"
                        }

TWITTER_ACCOUNT_HOTEL_IDS = { "@FabHotels":"2441658608",
                               "@TridentHotels":"32822724",
                               "@hotelavasa":"2819190702",
                               "@Westin":"47796779",
                               "@katriyahotels":"351406554"
                               }

argument_config = {
    'twitter_hashtags': os.getenv('TWITTER_HASHTAGS', TWITTER_ACCOUNT_IDS),
    'twitter_hashtags_hotels': os.getenv('TWITTER_HASHTAGS_HOTEL', TWITTER_ACCOUNT_HOTEL_IDS),
    #'twitter_keys' : os.getenv('TWITTER_KEYS', TWITTER_KEYS),
    'Zomato': os.getenv('ZOMATO', ''),
    'Google': os.getenv('GOOGLE', ''),
    'access_token' : os.getenv('ACCESS_TOKEN', ''),
    'access_token_secret':os.getenv('ACCESS_TOKEN_SECRET', ''),
    'consumer_secret':os.getenv('CONSUMER_SECRET', ''),
    'consumer_key': os.getenv('CONSUMER_KEY', '')
}


mongo_config = {
    'mongo_uri': os.getenv('MONGO_URI', ''),
    'db_name': os.getenv('MONGO_DB_NAME', ''),
    'col_name': os.getenv('MONGO_COL_NAME_DATA', ''),
    'col_name_hotel': os.getenv('MONGO_HOTEL_COL_NAME_DATA', ''),
    'col_name1': os.getenv('MONGO_COL_NAME_SENTIMENT', ''),
    'col_name2': os.getenv('MONGO_COL_NAME_FLASK_DATA', ''),
    'col_name3': os.getenv('MONGO_COL_NAME_FLASK_SENTIMENT', ''),
    'requires_auth': os.getenv('REQUIRES_AUTH', 'true'),
    'mongo_username': os.getenv('MONGO_USER', ''),
    'mongo_password': os.getenv('MONGO_PASSWORD', ''),
    'mongo_auth_source': os.getenv('MONGO_AUTH_SOURCE', ''),
    'mongo_auth_mechanism': os.getenv('MONGO_AUTH_MECHANISM', 'SCRAM-SHA-1'),
    'mongo_index_name': os.getenv('MONGO_INDEX_NAME', 'csrtc'),
    'ssl_required': os.getenv('MONGO_SSL_REQUIRED', True),
    'replicaSet': os.getenv('REPLICASET', '')
}
