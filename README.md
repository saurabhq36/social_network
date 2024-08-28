# social_network


Follow these steps to set up and run the project.

### 1. Clone the Repository

```bash
cd your-repository
docker-compose up --build -d
docker-compose run web python manage.py migrate
docker-compose run web python manage.py createsuperuser



