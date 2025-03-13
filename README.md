# RideShare Backend

This is the backend repository for the RideShare application, a Django-based project hosted with Nginx and Gunicorn.

## Live Deployment
[![Live](https://img.shields.io/badge/Live-https://ride.emplique.com-brightgreen)](https://ride.emplique.com/)
Check out the live application here: [RideShare](https://ride.emplique.com/)

## Deployment
The application is automatically deployed to a VPS (203.161.48.190) using GitHub Actions whenever code is pushed to the `main` branch. View the workflow status [here](https://github.com/IamNishanKhan/RideShareBackend/actions).

## Setup
- Hosted on Ubuntu server.
- Uses Gunicorn as the WSGI server and Nginx as the reverse proxy.
- Secured with Let’s Encrypt SSL.

## Contributing
Feel free to submit issues or pull requests!