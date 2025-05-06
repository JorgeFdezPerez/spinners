# Official MySQL image
FROM mysql:latest

# Default container configuration folder
ARG CONFIG_PATH="configuration"

# Copy init files for the database
COPY $CONFIG_PATH/* /docker-entrypoint-initdb.d/

# Set the default user for the MySQL image
#USER mysql

# If we need to create new users
#RUN mysql -u root -p -e "CREATE USER '$MYSQL_USER'@'%' IDENTIFIED BY '$MYSQL_PASSWORD';"
#RUN mysql -u root -p -e "GRANT ALL PRIVILEGES ON $MYSQL_DATABASE.* TO '$MYSQL_USER'@'%';"
#RUN mysql -u root -p -e "FLUSH PRIVILEGES;"
#RUN create user 'user'@'%' identified by 'pass';
#RUN grant all privileges on *.* to 'user'@'%' with grant option;
#RUN flush privileges;

# Expose port 3306 to allow connections to the database
EXPOSE 3306

# Start the MySQL server when the container is run
CMD ["mysqld"]