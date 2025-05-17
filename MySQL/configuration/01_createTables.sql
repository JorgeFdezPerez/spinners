/*
 * Creating database tables
*/

DROP DATABASE IF EXISTS spinners;
CREATE DATABASE IF NOT EXISTS spinners;
USE spinners;

DROP TABLE IF EXISTS recetas_maestras,
                     recetas_control,
                     lotes,
                     fases_equipamiento,
                     modulos_equipamiento,
                     variables_me,
                     usuarios,
                     etapas, 
                     transiciones, 
                     parametros,
                     valores_parametros;

SELECT 'CREATING TABLES' as 'INFO';

CREATE TABLE usuarios (
    id_usuario INT NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(255) NOT NULL,
    PRIMARY KEY (id_usuario)
);

CREATE TABLE recetas_maestras (
    id_receta_maestra INT NOT NULL AUTO_INCREMENT,
    id_usuario INT NOT NULL,
    codigo_receta_maestra VARCHAR(255) NOT NULL,
    descripcion VARCHAR(255),
    fecha_creada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_receta_maestra),
    UNIQUE KEY (codigo_receta_maestra),
    FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE recetas_control (
    id_receta_control INT NOT NULL AUTO_INCREMENT,
    id_receta_maestra INT NOT NULL,
    id_usuario INT NOT NULL,
    fecha_creada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cantidad_producida INT NOT NULL,
    PRIMARY KEY (id_receta_control),
    FOREIGN KEY (id_receta_maestra) REFERENCES recetas_maestras (id_receta_maestra) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE alarmas (
    id_alarma INT NOT NULL AUTO_INCREMENT,
    id_receta_control INT NOT NULL,
    descripcion VARCHAR(255),
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_alarma),
    FOREIGN KEY (id_receta_control) REFERENCES recetas_control (id_receta_control) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE parametros (
    id_parametro INT NOT NULL AUTO_INCREMENT,
    id_receta_maestra INT NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    tipo VARCHAR(255) NOT NULL,
    PRIMARY KEY (id_parametro),
    FOREIGN KEY (id_receta_maestra) REFERENCES recetas_maestras (id_receta_maestra) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE valores_parametros (
    id_valor_parametro INT NOT NULL AUTO_INCREMENT,
    id_parametro INT NOT NULL,
    id_receta_control INT NOT NULL,
    valor VARCHAR(255) NOT NULL,
    PRIMARY KEY (id_valor_parametro),
    FOREIGN KEY (id_parametro) REFERENCES parametros (id_parametro) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_receta_control) REFERENCES recetas_control (id_receta_control) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE lotes (
    id_lote INT NOT NULL AUTO_INCREMENT,
    id_receta_control INT NOT NULL,
    PRIMARY KEY (id_lote),
    FOREIGN KEY (id_receta_control) REFERENCES recetas_control (id_receta_control) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE modulos_equipamiento (
    id_modulo_equipamiento INT NOT NULL AUTO_INCREMENT,
    codigo_modulo_equipamiento VARCHAR(255) NOT NULL,
    node_id_modulo_equipamiento VARCHAR(255) NOT NULL,
    PRIMARY KEY (id_modulo_equipamiento),
    UNIQUE KEY (codigo_modulo_equipamiento),
    UNIQUE KEY (node_id_modulo_equipamiento)
);

CREATE TABLE variables_me (
    id_variable_me INT NOT NULL AUTO_INCREMENT,
    id_modulo_equipamiento INT NOT NULL,
    codigo_variable_me VARCHAR(255) NOT NULL,
    node_id_variable_me VARCHAR(255) NOT NULL,
    tipo VARCHAR(255),
    permiso VARCHAR(1),
    descripcion VARCHAR(255),
    PRIMARY KEY (id_variable_me),
    UNIQUE KEY (node_id_variable_me),
    FOREIGN KEY (id_modulo_equipamiento) REFERENCES modulos_equipamiento (id_modulo_equipamiento) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE fases_equipamiento (
    id_fase_equipamiento INT NOT NULL AUTO_INCREMENT,
    id_modulo_equipamiento INT NOT NULL,
    num_srv INT NOT NULL,
    descripcion VARCHAR(255),
    PRIMARY KEY (id_fase_equipamiento),
    FOREIGN KEY (id_modulo_equipamiento) REFERENCES modulos_equipamiento (id_modulo_equipamiento) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE etapas (
    id_etapa INT NOT NULL AUTO_INCREMENT,
    id_receta_maestra INT NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    es_inicial BOOL NOT NULL,
    es_final BOOL NOT NULL,
    PRIMARY KEY (id_etapa),
    FOREIGN KEY (id_receta_maestra) REFERENCES recetas_maestras (id_receta_maestra) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE fases_etapas (
    id_fases_etapas INT NOT NULL AUTO_INCREMENT,
    id_fase_equipamiento INT NOT NULL,
    id_etapa INT NOT NULL,
    id_parametro_setpoint INT,
    PRIMARY KEY (id_fases_etapas),
    FOREIGN KEY (id_fase_equipamiento) REFERENCES fases_equipamiento (id_fase_equipamiento) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_etapa) REFERENCES etapas (id_etapa) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_parametro_setpoint) REFERENCES parametros (id_parametro) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE condiciones (
    id_condicion INT NOT NULL AUTO_INCREMENT,
    id_variable_me INT NOT NULL,
    equals BIT NOT NULL,
    PRIMARY KEY (id_condicion),
    FOREIGN KEY (id_variable_me) REFERENCES variables_me (id_variable_me) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE transiciones (
    id_transicion INT NOT NULL AUTO_INCREMENT,
    id_etapa_inicial INT NOT NULL,
    id_etapa_final INT NOT NULL,
    id_condicion INT,
    PRIMARY KEY (id_transicion),
    FOREIGN KEY (id_etapa_inicial) REFERENCES etapas (id_etapa) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_etapa_final) REFERENCES etapas (id_etapa) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_condicion) REFERENCES condiciones (id_condicion) ON UPDATE CASCADE ON DELETE RESTRICT
);

SELECT 'TABLES CREATED' as 'INFO';