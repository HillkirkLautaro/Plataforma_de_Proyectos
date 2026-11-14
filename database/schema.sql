-- Esquema DDL SQL para MySQL
CREATE DATABASE IF NOT EXISTS portfolio_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE portfolio_db;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    nombre_completo VARCHAR(100),
    bio TEXT,
    rol ENUM('usuario', 'admin') DEFAULT 'usuario' NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS usuario_habilidades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    tecnologia_id INT NOT NULL,
    nivel ENUM('básico', 'intermedio', 'avanzado') NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    UNIQUE KEY uk_usuario_tec (usuario_id, tecnologia_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS proyectos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    nombre VARCHAR(120) NOT NULL,
    descripcion TEXT,
    etapa ENUM('formulación', 'modelado', 'implementación', 'testing', 'producción', 'mantenimiento') NOT NULL,
    fecha_inicio DATE NULL,
    fecha_fin DATE NULL,
    deadline DATE NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS proyecto_tecnologias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    proyecto_id INT NOT NULL,
    tecnologia_id INT NOT NULL,
    nivel ENUM('básico', 'intermedio', 'avanzado') NOT NULL DEFAULT 'intermedio',
    FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON DELETE CASCADE,
    UNIQUE KEY uk_proy_tec (proyecto_id, tecnologia_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS proyecto_lenguajes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    proyecto_id INT NOT NULL,
    lenguaje_id INT NOT NULL,
    nivel ENUM('básico', 'intermedio', 'avanzado') NOT NULL DEFAULT 'intermedio',
    FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON DELETE CASCADE,
    UNIQUE KEY uk_proy_len (proyecto_id, lenguaje_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS proyecto_links (
    id INT AUTO_INCREMENT PRIMARY KEY,
    proyecto_id INT NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    url VARCHAR(255) NOT NULL,
    FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON DELETE CASCADE
) ENGINE=InnoDB;
