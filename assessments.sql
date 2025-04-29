CREATE TABLE assessments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assessment_name VARCHAR(255) NOT NULL,
    import_date DATETIME NOT NULL,
    department VARCHAR(255) NOT NULL,
    upload_date DATETIME NOT NULL,
    template_path VARCHAR(500) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);