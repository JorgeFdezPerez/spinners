USE spinners;

SELECT 'LOADING EQUIPMENT MODULES DATA' as 'INFO';

LOAD DATA INFILE '/var/lib/mysql-files/modulos_equipamiento.csv' INTO TABLE modulos_equipamiento
FIELDS TERMINATED by ';' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 LINES;

LOAD DATA INFILE '/var/lib/mysql-files/fases_equipamiento.csv' INTO TABLE fases_equipamiento
FIELDS TERMINATED by ';' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 LINES;

LOAD DATA INFILE '/var/lib/mysql-files/variables_me.csv' INTO TABLE variables_me
FIELDS TERMINATED by ';' ENCLOSED BY '"' LINES TERMINATED BY '\n'
IGNORE 1 LINES;

SELECT 'EQUIPMENT MODULES LOADED' as 'INFO';