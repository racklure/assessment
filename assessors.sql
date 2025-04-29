CREATE TABLE assessors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    group_name VARCHAR(255) NOT NULL,
    frequency ENUM('monthly', 'quarterly') NOT NULL,
    score_weight DECIMAL(5,2) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);