# social_network


Follow these steps to set up and run the project.

1. Clone the Repository

2. cd your-repository

#run following command to Build and Start the Docker Containers
3. docker-compose up --build -d && docker-compose run web python manage.py migrate

#create super user
4. docker-compose run web python manage.py createsuperuser

#access the admin portal
5. The program must be running on  8000 port -- > http://localhost:8000/admin/

############### Postman collection ###################
Once your project is running, follow these steps to test the APIs using Postman:

Open Postman

Import the Postman collection and the associated environment (e.g., dev) into Postman.
Hit the Signup API

Start by hitting the signup API to create a new user.
Test the Login API

Next, test the login API. Upon successful login, this API will return a token.
Use the Token for Authentication

The token returned from the login API can be used to authenticate subsequent API requests. Make sure to include this token in the Authorization header for any other API calls you make.





