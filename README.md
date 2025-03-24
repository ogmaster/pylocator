# Distributed Object Tracking System

A real-time system for tracking, visualizing, and analyzing object movements across distributed environments.

![Distributed Object Tracking System](https://via.placeholder.com/800x400?text=Distributed+Object+Tracking+System)

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Running the Application](#running-the-application)

## Overview

The Distributed Object Tracking System provides a comprehensive solution for monitoring and analyzing the movement of objects in real-time. It includes visualization tools, historical data analysis, event tracking, and zone management capabilities.

## Features

- **Real-time Tracking**: Monitor object positions with configurable update frequency
- **Historical Analysis**: Visualize object movement paths with smooth playback animation
- **Event Monitoring**: Track object appearances, disappearances, and zone interactions
- **Analytics**: Generate heatmaps of object activity
- **Zone Management**: Create and manage detection zones for triggering events
- **Responsive UI**: User-friendly dashboard with multiple visualization options

## System Architecture

The system consists of several components:

- **Dashboard App**: Dash-based web application for visualization and control
- **API Service**: FastAPI backend for data retrieval and processing
- **MQTT Broker**: Handles real-time messaging between components
- **Data Processor**: Processes incoming position data
- **Simulator**: Generates test data for development and demonstrations
- **Database**: Stores object data, events, and configuration

## Running The Application

### Start the Services

#### Using Docker Compose (recommended)

```bash
docker-compose up -d
```

This will start all required services:
- MQTT Broker
- API Service
- Data Processor
- MongoDB
- InfluxDB
- Simulator (if enabled)
- Dashboard App


### Access the Dashboard

Open your browser and navigate to: 

http://localhost:8050