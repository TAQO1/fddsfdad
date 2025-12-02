# Health & Fitness Club Management System


######################
Proj structure

FITNESS_PROJECT
models          # ORM entitty classes

models.py      # all database models like Member trainer and so on

__init__.py    # package initialization

/app             

main.py        # Main app/cui

docs            # documentation

README.md      # This file

ERD.pdf        # ER diagram and Mapping and normalization

requirements.txt # Py dependencies



######################



Set up PostgreSQL database:
    make a database named fitness_club in PostgreSQL
    Update database credentials in `app/main.py` if needed:
 
     DB_NAME = "fitness_club"
     DB_USER = "postgres"
     DB_PASSWORD = 
     DB_HOST = "localhost"
     DB_PORT = "5432"
     

The schema will be created automatically when you first run the application

-----------

Running the app:

From this folder Install dependencies if needed:
'py -m pip install -r requirements.txt'

then run 'py app.py'

######################

VIDEO

LINK: https://youtu.be/nGM74g73Wl8

#######################