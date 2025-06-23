FROM python:latest

# Default container configuration folder
ARG CONFIG_PATH="configuration"

COPY $CONFIG_PATH/* /home/interfaz

# upgrade pip version
RUN pip install --upgrade pip

# Install dependencies

RUN pip install asyncua
RUN pip install opcua
RUN pip install streamlit
RUN pip install mysql-connector-python
RUN pip install pymysql
RUN pip install SQLAlchemy

#COPY requirements.txt /tmp/requirements.txt
#RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt

CMD [ "python", "-m", "streamlit", "run", "/home/interfaz/interfaz/inter_stream.py", "--server.port=2000" ]
EXPOSE 2000