from datetime import datetime, timedelta
import hashlib
from bs4 import BeautifulSoup, Tag
import logging
import requests
from 0_Mongo_Connector import  update_mongo_collection, initialize_mongo
from 0_config import mongo_config, argument_config
import tweepy
import json
import time
from dateutil.parser import parse
import re
from 2_ABSA_v2 import load_sentiments_to_mongo

class SentimentAnalysis(object):
    def __init__(self, apiKey):
        super(SentimentAnalysis, self).__init__()
        self.apiKey = apiKey

    def get_location_id(self, location, latitude, longitude, count):
        endpoint_url = "https://developers.zomato.com/api/v2.1/locations"
        places = []
        headers = {
            "Accept": "application/json",
            "user-key": self.apiKey }
        params = {
            'query': location,
            'lat': latitude,
            'lon': longitude,
            'count': count
        }
        res = requests.get(endpoint_url, headers=headers, params = params)
        results = res.json()
        for entity in results["location_suggestions"]:
            entity_dict = {}
            entity_dict["entity_type"] = entity["entity_type"]
            entity_dict["entity_id"] = entity["entity_id"]
            places.append(entity_dict)
        return places

    def get_restaurent_id(self, entity_id, entity_type):
        endpoint_url = "https://developers.zomato.com/api/v2.1/location_details"
        res_id = []
        headers = {
            "Accept": "application/json",
            "user-key": self.apiKey }
        params = {
            'entity_id': entity_id,
            'entity_type': entity_type
        }
        res = requests.get(endpoint_url, headers=headers, params=params)
        location_resp = res.json()
        res_id.extend(location_resp["best_rated_restaurant"])
        return res_id

    def get_zomato_reviews(self, restaurant_id, start, count):
        endpoint_url = "https://developers.zomato.com/api/v2.1/reviews"
        headers = {
            "Accept": "application/json",
            "user-key": self.apiKey }
        params = {
            'res_id': restaurant_id,
            'start': start,
            'count': count
        }
        res = requests.get(endpoint_url, headers=headers, params=params)
        return res.json()

    def date_conv(self, date):
        if "hours" in date or date.split("-")[0].isdigit():
            return datetime.today().date()
        elif "days" in date:
            d = datetime.today() - timedelta(int(date.split(" ")[0]))
            return d.date()
        elif "months" in date:
            m = datetime.today() - timedelta(int(date.split(" ")[0])*30)
            return m.date()
        elif "yesterday" in date:
            yesdy = datetime.today() - timedelta(1)
            return yesdy.date()
        else:
            return datetime.today().date()

    def search_places_by_coordinate(self, location, radius, types):
        endpoint_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        places = []
        params = {
            'location': location,
            'radius': radius,
            'types': types,
            'key': self.apiKey
        }
        res = requests.get(endpoint_url, params = params)
        results =  json.loads(res.content.decode('utf-8'))
        places.extend(results['results'])
        time.sleep(2)
        while "next_page_token" in results:
            params['pagetoken'] = results['next_page_token'],
            res = requests.get(endpoint_url, params = params)
            results = json.loads(res.content.decode('utf-8'))
            places.extend(results['results'])
            time.sleep(2)
        return places

    def get_place_details(self, place_id, fields):
        endpoint_url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            'placeid': place_id,
            'fields': ",".join(fields),
            'key': self.apiKey
        }
        res = requests.get(endpoint_url, params = params)
        place_details =  json.loads(res.content.decode('utf-8'))
        return place_details

    def dateconverter(self, date):
        if "last week" in date or "a week ago" in date:
            N = 7
            return N
        elif "weeks" in date:
            return int(date.split(" ")[0])*7
        elif "month" in date:
            N = 30
            return N
        elif "months" in date:
            return int(date.split(" ")[0])*30
        elif "a year" in date:
            N = 365
            return N
        elif "years" in date:
            return int(date.split(" ")[0])*365
        else:
            return ""

def remove_emoji(text):
    emoji_pattern = re.compile("["
                    u"\U0001F600-\U0001F64F"  # emoticons
                    u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                    u"\U0001F680-\U0001F6FF"  # transport & map symbols
                    u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                    u"\U00002702-\U000027B0"
                    u"\U000024C2-\U0001F251"
                    u"\U0001f926-\U0001f937"
                    u'\U00010000-\U0010ffff'
                    u"\u200d"
                    u"\u2640-\u2642"
                    u"\u2600-\u2B55"
                    u"\u23cf"
                    u"\u23e9"
                    u"\u231a"
                    u"\u3030"
                    u"\ufe0f"
        "]+", flags=re.UNICODE)

    return emoji_pattern.sub(r'', text)

def citysearch_reviews(obj):
    logging.info("Extracting reviews from city search")
    '''extracting reviews from city search site for houston region'''
    feed_obj = []
    F_resp = requests.get("http://www.citysearch.com/listings/houston-tx-metro/restaurants.html")
    soup = BeautifulSoup(F_resp.content,"html.parser")
    soup1 = soup.find("div",{"class":"unit size4of12"})
    for a2 in soup1.find_all("div",{"class":"inner row block"}):
        link_url = a2.find("a")["href"]
        S_resp = requests.get(link_url)
        soup2 = BeautifulSoup(S_resp.content,"html.parser")
        H_resp1 = soup2.find("div",{"class":"row relative boards center clip"})
        try:
            for a2 in H_resp1.find("ul",{"class":"js-masonry center jsInvisible"}).find_all("li"):
                if isinstance(a2, Tag):
                    link = a2.find("div",{"class":"row"}).find("a")["href"]
                    link1 = "http://www.citysearch.com"+str(link)
                    T_resp = requests.get(link1)
                    soup3 = BeautifulSoup(T_resp.content,"html.parser")
                    F_resp3 = soup3.find("div",{"class":"unit size9of12"})
                    restaurant_name = F_resp3.find("div",{"id":"nameModule"}).find("h1").text.strip()
                    city = F_resp3.find("div",{"id":"nameAddressModule"}).find("span",{"class":"locality"}).text.strip()
                    F_resp2 = soup3.find("div",{"id":"internalExternalTips"}).find_all("div",{"class":"clip"})

                    for content in F_resp2:
                        resp_dict = {}
                        resp_dict["Extracted_Date"] = str(datetime.today().date())
                        resp_dict["Source"] = "CitySearch"
                        resp_dict["City"] = city
                        resp_dict["Country"] = "USA"
                        resp_dict["Restaurent_name/Hotel_name"] = restaurant_name
                        resp_dict["Area"] = str(city)+",USA"
                        resp_dict["Rating_text"] =  ""
                        resp_dict["Rating"] = ""
                        resp_dict["Max_Rating"] = "5"
                        resp_dict["Restaurent_id/Hotel_id"] = ""
                        try:
                            resp_dict["User_id"] = content["data-reviewid"]
                        except KeyError:
                            resp_dict["User_id"] = ""
                        resp_dict["User_Age"] = ""
                        resp_dict["User_Location"] = ""
                        resp_dict["User_Gender"] = ""
                        
                        content1 = content.find("div",{"class":"reviewer card row"})
                        if isinstance(content1, Tag):
                            try:
                                Posted_date = datetime.strptime(content1.find("span",{"class":"secondaryText left"}).find("meta")["content"],"%Y-%m-%d")
                            except KeyError:
                                Posted_date = datetime.today() - timedelta(10*365)
                            user_name = content1.find("div",{"class":"h5"}).find("a",{"class":"tinyPush slyLink"})
                            if isinstance(user_name, Tag):
                                resp_dict["User_Name"] = user_name.text.strip()
                            else:
                                resp_dict["User_Name"] = ""
                        else:
                            Posted_date = datetime.today() - timedelta(10*365)
                            resp_dict["User_Name"] = ""
                        try:
                            resp_dict["Review_Text"] = content.find("div",{"class":"box reviewBox relative"}).find("p").text.strip().replace("\n","").replace("\r","")
                        except KeyError:
                            resp_dict["Review_Text"] = ""
                        if obj is not None:
                            if Posted_date.date() > datetime.strptime(obj['Posted_date'], '%Y-%m-%d').date():
                                resp_dict["Posted_date"] = str(Posted_date.date())
                                checksum = hashlib.md5(json.dumps(resp_dict, sort_keys=True).encode('utf8')).hexdigest()
                                resp_dict['checksum'] = checksum
                                feed_obj.append(resp_dict.copy())
                        else:
                            resp_dict["Posted_date"] = str(Posted_date.date())
                            checksum = hashlib.md5(json.dumps(resp_dict, sort_keys=True).encode('utf8')).hexdigest()
                            resp_dict['checksum'] = checksum
                            feed_obj.append(resp_dict.copy())
        except:
            logging.warning("Issue while Souping URL")
            pass

    return feed_obj

def zomato_reviews(obj):
    logging.info("Extracting reviews provided by zomato via api")
    '''this function extracts reviews provided by zomato via api.'''
    apiKey = argument_config.get('Zomato')
    api = SentimentAnalysis(apiKey)
    reviewslist = []
    locations = ["madhapur","kondapur","kphp","banjarahills","secunderabad","Gachibowli","Miyapur"]
    for location in locations:
        places = api.get_location_id(location, 17.3850, 78.4867, 5)
        for place in places:
            resid = api.get_restaurent_id(place["entity_id"], place["entity_type"])
            try:
                for res in resid:
                    # provide restaurant id in order to get reviews of specific restaurant(manditory field)
                    reviews = api.get_zomato_reviews(res["restaurant"]["id"], "1", "20")
                    for everyreview in reviews["user_reviews"]:
                        ratingdict = {}
                        ratingdict["Extracted_Date"] = str(datetime.today().date())
                        ratingdict["Source"] = "Zomato"
                        ratingdict["City"] = "hyderabad"
                        ratingdict["Country"] = "India"
                        ratingdict["Restaurent_name/Hotel_name"] =  res["restaurant"]["name"]
                        ratingdict["Restaurent_id/Hotel_id"] = res["restaurant"]["id"]
                        ratingdict["Area"] = res["restaurant"]["location"]["locality"]
                        ratingdict["Rating"] = str(everyreview["review"]["rating"])
                        ratingdict["Max_Rating"] = "5"
                        ratingdict["Review_Text"] = remove_emoji(str(everyreview["review"]["review_text"])).replace("\n","").replace("\r","")
                        ratingdict["User_id"] = everyreview["review"]["id"]
                        ratingdict["Rating_text"] = everyreview["review"]["rating_text"]
                        date1 = api.date_conv(str(everyreview["review"]["review_time_friendly"]))
                        ratingdict["User_Name"] = everyreview["review"]["user"]["name"]
                        ratingdict["User_Age"] = ""
                        ratingdict["User_Location"] = ""
                        ratingdict["User_Gender"] = ""
                        
                        if obj is not None:
                            if date1>datetime.strptime(obj['Posted_date'], '%Y-%m-%d').date():
                                ratingdict["Posted_date"] = str(date1)
                                checksum = hashlib.md5(json.dumps(ratingdict, sort_keys=True).encode('utf8')).hexdigest()
                                ratingdict['checksum'] = checksum
                                reviewslist.append(ratingdict.copy())
                        else:
                            ratingdict["Posted_date"] = str(date1)
                            checksum = hashlib.md5(json.dumps(ratingdict, sort_keys=True).encode('utf8')).hexdigest()
                            ratingdict['checksum'] = checksum
                            reviewslist.append(ratingdict.copy())
            except:
                logging.warn("Issue while getting Zomato resID, please check API limit available for a day.")
                pass
    return reviewslist

def google_reviews(obj):
    logging.info("extracting google reviews by places api and searching the nearest restaurants by coordinate")
    feed_obj = []
    apiKey = argument_config.get('Google')
    api = SentimentAnalysis(apiKey)
    '''extracting google reviews by places api and searching the nearest restaurants by coordinate'''
    places = api.search_places_by_coordinate("17.450500,78.380890", "1000", "restaurant")
    fields = ['name', 'formatted_address', 'international_phone_number', 'website', 'rating', 'review']
    for place in places:
        details = api.get_place_details(place['place_id'], fields)
        try:
            for review in details['result']['reviews']:
                googledict  = {}
                googledict["Extracted_Date"] = str(datetime.today().date())
                googledict["Source"] = "Google"
                googledict["City"] = place["vicinity"].split(",")[-1].strip()
                googledict["Country"] = "India"
                googledict["Restaurent_name/Hotel_name"] = details['result']['name']
                googledict["Restaurent_id/Hotel_id"]=place['place_id']
                googledict["User_Name"] = review['author_name']
                googledict["Rating"] = str(review['rating'])
                googledict["Max_Rating"] = "5"
                googledict["Review_Text"] = remove_emoji(review['text']).replace("\n","").replace("\r","")
                date1 = api.dateconverter(review['relative_time_description'])
                Posted_date = datetime.now() - timedelta(days=date1)

                googledict["User_id"] = ""
                googledict["User_Age"] = ""
                googledict["User_Location"] = ""
                googledict["User_Gender"] = ""
                googledict["Rating_text"] = ""
                googledict["Area"] = place["vicinity"]
                if obj is not None:
                    if Posted_date.date()>datetime.strptime(obj['Posted_date'], '%Y-%m-%d').date():
                        googledict["Posted_date"] = str(Posted_date.date())
                        checksum = hashlib.md5(json.dumps(googledict, sort_keys=True).encode('utf8')).hexdigest()
                        googledict['checksum'] = checksum
                        feed_obj.append(googledict.copy())
                else:
                    googledict["Posted_date"] = str(Posted_date.date())
                    checksum = hashlib.md5(json.dumps(googledict, sort_keys=True).encode('utf8')).hexdigest()
                    googledict['checksum'] = checksum
                    feed_obj.append(googledict.copy())
        except:
            logging.warn("Issue while getting google placeid")
            pass
    return feed_obj

def google_reviews_hotels(obj):
    logging.info("extracting google reviews by places api and searching the nearest restaurants by coordinate")
    feed_obj = []
    apiKey = argument_config.get('Google')
    api = SentimentAnalysis(apiKey)
    '''extracting google reviews by places api and searching the nearest restaurants by coordinate'''

    places = api.search_places_by_coordinate("17.450500,78.380890", "1000", "hotels")
    fields = ['name', 'formatted_address', 'international_phone_number', 'website', 'rating', 'review']
    for place in places:
        details = api.get_place_details(place['place_id'], fields)
        try:
            for review in details['result']['reviews']:
                googledict  = {}
                googledict["Extracted_Date"] = str(datetime.today().date())
                googledict["Source"] = "Google"
                googledict["City"] = place["vicinity"].split(",")[-1].strip()
                googledict["Country"] = "India"
                googledict["Restaurent_name/Hotel_name"] = details['result']['name']
                googledict["Restaurent_id/Hotel_id"]=place['place_id']
                googledict["User_Name"] = review['author_name']
                googledict["Rating"] = str(review['rating'])
                googledict["Max_Rating"] = "5"
                googledict["Review_Text"] = remove_emoji(review['text']).replace("\n","").replace("\r","")
                date1 = api.dateconverter(review['relative_time_description'])
                Posted_date = datetime.now() - timedelta(days=date1)

                googledict["User_id"] = ""
                googledict["User_Age"] = ""
                googledict["User_Location"] = ""
                googledict["User_Gender"] = ""
                googledict["Rating_text"] = ""
                googledict["Area"] = place["vicinity"]
                if obj is not None:
                    if Posted_date.date()>datetime.strptime(obj['Posted_date'], '%Y-%m-%d').date():
                        googledict["Posted_date"] = str(Posted_date.date())
                        checksum = hashlib.md5(json.dumps(googledict, sort_keys=True).encode('utf8')).hexdigest()
                        googledict['checksum'] = checksum
                        feed_obj.append(googledict.copy())
                else:
                    googledict["Posted_date"] = str(Posted_date.date())
                    checksum = hashlib.md5(json.dumps(googledict, sort_keys=True).encode('utf8')).hexdigest()
                    googledict['checksum'] = checksum
                    feed_obj.append(googledict.copy())
        except:
            logging.warn("Issue while getting google placeid")
            pass
    return feed_obj

def twitter_reviews(obj):
    logging.info("searching the twitter reviews or orginal tweets posted by the user for specific handles")
    '''searching the twitter reviws or orginal tweets posted by the user for specific handles'''
    feed_obj = []
    auth = tweepy.OAuthHandler(argument_config.get('consumer_key'), argument_config.get('consumer_secret'))
    auth.set_access_token(argument_config.get('access_token'), argument_config.get('access_token_secret'))
    api = tweepy.API(auth,wait_on_rate_limit = True)
    twitter_hashtags = argument_config.get('twitter_hashtags')
    try:
        for handle in twitter_hashtags.keys():
            time.sleep(60)
            tweets = tweepy.Cursor(api.search, q=handle, rpp=100).items(300)
            for tweet in tweets:
                if tweet._json["in_reply_to_status_id"] == None and tweet._json["in_reply_to_status_id_str"] == None: #and tweet._json["retweet_count"] == 0
                    json_dict = {}
                    json_dict["Extracted_Date"] = str(datetime.today().date())
                    json_dict["Source"]="Twitter"
                    json_dict["Review_Text"]=remove_emoji(tweet._json["text"].strip()).replace("\n","").replace("\r","")
                    json_dict["User_Name"]=tweet._json["user"]["name"]
                    json_dict["User_Age"] = ""
                    json_dict["User_Location"] = ""
                    json_dict["User_Gender"] = ""
                    json_dict["User_id"]=tweet._json["user"]["id_str"]
                    json_dict["Posted_date"]=tweet._json["user"]["created_at"]
                    dt = parse(tweet._json["user"]["created_at"])
                    json_dict["Posted_date"]=dt.date()
                    if tweet._json["user"]["location"]:
                        json_dict["Country"]=tweet._json["user"]["location"]
                    else:
                        json_dict["Country"] = "India"
                    json_dict["City"]=""
                    json_dict["Area"]="India"
                    json_dict["Rating_text"]=""
                    json_dict["Rating"]=""
                    json_dict["Max_Rating"] = "5"
                    for user in tweet._json["entities"]["user_mentions"]:
                        json_dict["Restaurent_name/Hotel_name"] = user["name"]
                        json_dict["Restaurent_id/Hotel_id"] = user["id_str"]
                    if obj is not None:
                        if dt.date()>datetime.strptime(obj['Posted_date'], '%Y-%m-%d').date():
                            json_dict["Posted_date"] = str(dt.date())
                            checksum = hashlib.md5(json.dumps(json_dict, sort_keys=True).encode('utf8')).hexdigest()
                            json_dict['checksum'] = checksum
                            feed_obj.append(json_dict.copy())
                    else:
                        json_dict["Posted_date"] = str(dt.date())
                        checksum = hashlib.md5(json.dumps(json_dict, sort_keys=True).encode('utf8')).hexdigest()
                        json_dict['checksum'] = checksum
                        feed_obj.append(json_dict.copy())
    except:
        logging.warn("Issue while extracting data from Twitter handle, please recheck expiry/limits of keys.")
        pass
    return feed_obj

def twitter_reviews_hotels(obj):
    logging.info("searching the twitter reviews or orginal tweets posted by the user for specific handles")
    '''Searching the twitter reviews or orginal tweets posted by the user for specific handles'''
    feed_obj = []
    auth = tweepy.OAuthHandler(argument_config.get('consumer_key'), argument_config.get('consumer_secret'))
    auth.set_access_token(argument_config.get('access_token'), argument_config.get('access_token_secret'))
    api = tweepy.API(auth,wait_on_rate_limit = True)
    twitter_hashtags = argument_config.get('twitter_hashtags_hotels')
    try:
        for handle in twitter_hashtags.keys():
            time.sleep(60)
            tweets = tweepy.Cursor(api.search, q=handle, rpp=100).items(300)
            for tweet in tweets:
                if tweet._json["in_reply_to_status_id"] == None and tweet._json["in_reply_to_status_id_str"] == None: #and tweet._json["retweet_count"] == 0
                    json_dict = {}
                    json_dict["Extracted_Date"] = str(datetime.today().date())
                    json_dict["Source"]="Twitter"
                    json_dict["Review_Text"]=remove_emoji(tweet._json["text"].strip()).replace("\n","").replace("\r","")
                    json_dict["User_Name"]=tweet._json["user"]["name"]
                    json_dict["User_Age"] = ""
                    json_dict["User_Location"] = ""
                    json_dict["User_Gender"] = ""
                    json_dict["User_id"]=tweet._json["user"]["id_str"]
                    json_dict["Posted_date"]=tweet._json["user"]["created_at"]
                    dt = parse(tweet._json["user"]["created_at"])
                    json_dict["Posted_date"]=dt.date()
                    if tweet._json["user"]["location"]:
                        json_dict["Country"]=tweet._json["user"]["location"]
                    else:
                        json_dict["Country"] = "India"
                    json_dict["City"]=""
                    json_dict["Area"]="India"
                    json_dict["Rating_text"]=""
                    json_dict["Rating"]=""
                    json_dict["Max_Rating"] = "5"
                    for user in tweet._json["entities"]["user_mentions"]:
                        json_dict["Restaurent_name/Hotel_name"] = user["name"]
                        json_dict["Restaurent_id/Hotel_id"] = user["id_str"]
                    if obj is not None:
                        if dt.date()>datetime.strptime(obj['Posted_date'], '%Y-%m-%d').date():
                            json_dict["Posted_date"] = str(dt.date())
                            checksum = hashlib.md5(json.dumps(json_dict, sort_keys=True).encode('utf8')).hexdigest()
                            json_dict['checksum'] = checksum
                            feed_obj.append(json_dict.copy())
                    else:
                        json_dict["Posted_date"] = str(dt.date())
                        checksum = hashlib.md5(json.dumps(json_dict, sort_keys=True).encode('utf8')).hexdigest()
                        json_dict['checksum'] = checksum
                        feed_obj.append(json_dict.copy())
    except:
        logging.warn("Issue while extracting data from Twitter handle, please recheck expiry/limits of keys.")
        pass
    return feed_obj

def hotel_mongo_load():
    col_name = mongo_config.get('col_name_hotel')
    # Initializing Mongo With Collection Name
    mongo_colln = initialize_mongo(col_name)
    try:
        # Checking for latest date for data in Mongo
        if mongo_colln.find().sort("Posted_date", -1).limit(1).count()>0:
            logging.info("Checking for latest date for data in Database for Incremental Inserting")
            
            for obj in mongo_colln.find().sort("Posted_date", -1).limit(1):
                logging.info("Calling Sources functions for Extraction")
                scrapers  = [google_reviews_hotels(obj),twitter_reviews_hotels(obj)]
                for scraper in scrapers:
                    logging.info("Adding data to database collections.")
                    for each in scraper:
                        update_mongo_collection(mongo_colln, each["checksum"], each)
        elif mongo_colln.find().sort("Posted_date", -1).limit(1).count() == 0:
            logging.info("No Latest Date found, Collection is Empty. Inserting from beginning.")
            obj = None
            scrapers  = [google_reviews_hotels(obj),twitter_reviews_hotels(obj)]
            
            for scraper in scrapers:
                logging.info("Adding data to database collections.")
                for each in scraper:
                    update_mongo_collection(mongo_colln, each["checksum"], each)
    except:
        logging.error("Hotel Source Extractions threw an error. ")
        pass

def main():
    logging.basicConfig(filename='Reviews-Extractor-logs.log',
                        filemode='w',
                        format='%(asctime)s %(levelname)s \
                        %(module)s.%(funcName)s :: %(message)s',
                        datefmt='%d:%m:%y %H:%M:%S',
                        level=logging.INFO)
    col_name = mongo_config.get('col_name')
    # Initializing Mongo With Collection Name
    try:
        logging.info("Starting Hotel Reviews load to Mongo")
        hotel_mongo_load()
    except:
        logging.warn("Issue while loading Hotel Reviews to Mongo")
        pass
    logging.info("Starting Restaurant Reviews load to Mongo")
    mongo_colln = initialize_mongo(col_name)
    try:
        #Checking for latest date for data in Mongo
        if mongo_colln.find().sort("Posted_date", -1).limit(1).count()>0:
            logging.info("Checking for latest date for data in Database for Incremental Inserting")
            for obj in mongo_colln.find().sort("Posted_date", -1).limit(1):

                logging.info("Calling Sources functions for Extraction")
                scrapers  = [google_reviews(obj),zomato_reviews(obj),citysearch_reviews(obj),twitter_reviews(obj)]
                for scraper in scrapers:

                    logging.info("Adding data to database collections.")
                    for each in scraper:
                        update_mongo_collection(mongo_colln, each["checksum"], each)
        elif mongo_colln.find().sort("Posted_date", -1).limit(1).count() == 0:
            logging.info("No Latest Date found, Collection is Empty. Inserting from beginning.")
            obj = None
            scrapers  = [google_reviews(obj),zomato_reviews(obj),citysearch_reviews(obj),twitter_reviews(obj)]
            for scraper in scrapers:
                logging.info("Adding data to database collections.")
                for each in scraper:
                    update_mongo_collection(mongo_colln, each["checksum"], each)
    except:
        logging.error("Restaurant Source Extractions threw an error. ")
        pass

if __name__ == '__main__':
    while True:
        main()
        
        logging.info("Sleep Mode On for 100 secs before fetching Sentiment and aspect.")
        time.sleep(100)
        logging.info("Sentiment and Aspect Starting")
        
        # Upload sentiments to Mongo
        load_sentiments_to_mongo()
        logging.info("Today's Output Stored in Collection. Rescheduled for tomorrow. Thank You!!!")
        
        # Schedule script for 24hrs
        time.sleep(86400)
        
