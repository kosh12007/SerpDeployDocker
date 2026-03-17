CREATE TABLE IF NOT EXISTS parsing_positions_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    project_id INT,
    parsing_variant_id INT,
    status VARCHAR(50) DEFAULT 'pending',
    created_at DATETIME,
    completed_at DATETIME,
    spent_limits INT DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (parsing_variant_id) REFERENCES parsing_variants(id)
);