FROM python:latest

# upgrade pip version
RUN pip install --upgrade pip

# Install dependencies

RUN pip install asyncua
RUN pip install opcua
RUN pip install transitions
RUN pip install mysql-connector-python
RUN pip install reflex
RUN pip install graphviz
RUN pip install streamlit
RUN pip install pymysql
# For installing graphviz package to generate docs of state machines
RUN apt-get update
RUN yes | apt install software-properties-common
RUN apt-get update
RUN add-apt-repository "deb http://archive.ubuntu.com/ubuntu $(lsb_release -sc) universe"
RUN yes | apt-get install graphviz

#COPY requirements.txt /tmp/requirements.txt
#RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt