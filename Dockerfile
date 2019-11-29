FROM python:3.6
WORKDIR /app
ADD requirements.txt /app/requirements.txt
RUN pip install torch --no-cache-dir
RUN pip install torchvision --no-cache-dir
RUN pip install pytorch-pretrained-bert --no-cache-dir
RUN pip install ipython
RUN pip install -r /app/requirements.txt
RUN python -m spacy download en_core_web_sm --no-cache-dir
RUN wget https://sentiment-analysis-models.s3.ap-south-1.amazonaws.com/asc/model.pt -P /asc/
RUN wget https://sentiment-analysis-models.s3.ap-south-1.amazonaws.com/rest_pt/pytorch_model.bin -P /rest_pt/

ADD . /app
ENV PORT 9999
RUN chmod 777 entrypoint.sh
RUN chmod 777 app.py
RUN chmod 777 Reviews-Extractor.py
CMD ./entrypoint.sh
