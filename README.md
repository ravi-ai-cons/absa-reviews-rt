# absa-reviews
Aspect Based Sentiment Analysis for user reviews


* Dockerfile			- 	ADD requirements.txt /app/requirements.txt
					ADD . /app
					RUN chmod 777 entrypoint.sh
					RUN chmod 777 app.py
					RUN chmod 777 Reviews-Extractor.py
					CMD ./entrypoint.sh

* entrypoint.sh			- Docker points to this file to begin the execution of the application
					python Reviews-Extractor.py &
					python app.py

* app.py				- Flask application for testing individual reviews							

* Reviews_Extractor.py 		- To extract reviews from various sources

* Restaurants_Train.xml		- To parse aspects from the reviews

*ABSA_Data_Utils.py		- BERT tokenization.

 * ABSA_Retraining.py		- Builds and retrains the ML model upon BERT with the extracted reviews.

 *ABSA_v2.py			- Preprocess and builds the ML model with the help of pretrained BERTget polarities for restaurant reviews

