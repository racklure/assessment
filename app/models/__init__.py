from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .user import User
from .assessor import Assessor, AssessorGroup, AssessorAssessee
from .department import Department