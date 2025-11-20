# Hospital Digital Twin System

This system is a digital twin simulator for hospital operations, designed to simulate the various processes and resource scheduling of a real hospital.

## Video Demo

[![Video Demo](https://img.youtube.com/vi/I3LzZKzMB1I/hqdefault.jpg)](https://www.youtube.com/watch?v=I3LzZKzMB1I)

## Project Structure

- `server.py`: The main entry point for the application. It starts a web server to host the frontend and provide a REST API for the simulation.
- `backend/system.py`: Contains the core logic for setting up and running the simulation.
- `backend/models/Hospital.py`: The main hospital class, which simulates hospital operations and resource management.
- `backend/models/Patient.py`: The patient class, containing patient attributes and medical records.
- `backend/models/Doctor.py`: The doctor class, containing doctor's specialties and scheduling information.
- `frontend/`: Contains the HTML, CSS, and JavaScript for the web-based user interface.
- `default.yaml`: The configuration file for the simulation.

## Features

- **Patient Flow Simulation**: Simulates the entire patient journey from admission to discharge.
- **Resource Scheduling**: Manages the scheduling of doctors and other medical resources.
- **Room and Equipment Management**: Tracks the allocation and availability of rooms and medical equipment.
- **Medical Record Maintenance**: Keeps a record of each patient's medical history, diagnoses, and treatments.
- **Financial and Billing Processing**: Simulates the billing and payment process for medical services.
- **Resource Utilization Statistics**: Generates statistics on the utilization of hospital resources.
- **Real-time Visualization**: Provides a web-based interface to visualize the simulation in real-time.

## Usage

To start the simulation, run the following command:

```bash
python server.py
```

Then, open your web browser and navigate to `http://localhost:8000` to view the simulation.

## MVP Version Description

This is a Minimum Viable Product (MVP) version of the system, which includes the following core features:

1.  Basic patient flow simulation.
2.  Doctor and resource allocation.
3.  Medical record management.
4.  Simple billing and financial tracking.
5.  Generation of statistical reports.
6.  A web-based user interface for real-time visualization.

## Future Expansion Plans

- More complex resource scheduling algorithms.
- Management of medical equipment and consumables.
- Employee scheduling system.
- Real-time monitoring and warning system.
- APIs for integration with existing hospital systems.
- Predictive analysis and optimization recommendations.
