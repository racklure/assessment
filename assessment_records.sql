CREATE TABLE assessment_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assessment_id INT NOT NULL,
    assessor_id INT NOT NULL,
    assessee_id INT NOT NULL,
    score_data JSON NOT NULL,
    photo_url VARCHAR(500),
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assessment_id) REFERENCES assessments(id),
    FOREIGN KEY (assessor_id) REFERENCES assessors(id),
    FOREIGN KEY (assessee_id) REFERENCES assessees(id)
);