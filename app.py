# Import the dependencies.
import numpy as np
import pandas as pd
import datetime as dt
from dateutil.relativedelta import relativedelta as rd

import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func

from flask import Flask, jsonify

#################################################
# Database Setup
#################################################
engine = create_engine("sqlite:///Resources/hawaii.sqlite")

# reflect an existing database into a new model
Base = automap_base()

# reflect the tables
Base.prepare(autoload_with=engine)

# Save references to each table
measurement = Base.classes.measurement
station = Base.classes.station

# Set key variables used by multiple flask routes/functions
print('Setting key variables for flask routes/functions...')
session = Session(engine)
first_date = (session.query(measurement.date).order_by(measurement.date).first())[0]
last_date = (session.query(measurement.date).order_by(measurement.date.desc()).first())[0]
most_active_station = session.query(measurement.station, func.count(measurement.station)).\
        group_by(measurement.station).order_by(func.count(measurement.station).desc()).all()[0][0]
session.close()

#################################################
# Flask Setup
#################################################
app = Flask(__name__)

#################################################
# Flask Routes
#################################################

@app.route("/")
def welcome():
    """List all available api routes."""
    print('Server request for home page...')
    return (
        f'Hawaii Weather Station Data ({first_date} - {last_date})<br/><hr>'
        f'Available routes:<br/>'
        f'<ol>'
        f'<li><a href="/api/v1.0/precipitation">/api/v1.0/precipitation</a> - precipation amounts for the last 12 months</li>'
        f'<li><a href="/api/v1.0/stations">/api/v1.0/stations</a> - list of weather stations</li>'
        f'<li><a href="/api/v1.0/tobs">/api/v1.0/tobs</a> - last 12 months of temperature observations for the most active station ({most_active_station})</li>'
        f'<li>/api/v1.0/&lt;start&gt; - minimum, average and maximum temperature on or after the start date (format: yyyy-mm-dd)</li>'
        f'Example: /api/v1.0/2016-08-23 for dates after August 23, 2016</li>'
        f'<li>/api/v1.0/&lt;start&gt;/&lt;end&gt; - minimum, average and maximum temperature from the start date to end date</li>'
        f'Example: /api/v1.0/2016-08-23/2017-08-23 for dates between August 23, 2016 and August 23, 2017</li>'
        f'</ol>'
    )

@app.route("/api/v1.0/precipitation")
def precipitation():
    """Function returns a JSON list of dates and precipitation amounts for the last 12 months."""
    print('Server request for precipitation data...')

    # Retrieve the last 12 months of precipitation data
    session = Session(engine)
    end_date = last_date
    start_date = str(dt.datetime.strptime(end_date, '%Y-%m-%d').date() - rd(months=12))
    precip_data = session.query(measurement.date, measurement.prcp).filter(measurement.date >= start_date).\
        filter(measurement.date <= end_date).all()
    session.close()
    
    # Create dictionary with precipitation data
    precip_list = []
    for date, prcp in precip_data:
        precip_dict = {}
        precip_dict["date"] = date
        precip_dict["prcp"] = prcp
        precip_list.append(precip_dict)

    # Return dictionary as JSON list
    return jsonify(precip_list) 

@app.route("/api/v1.0/stations")
def stations():
    """Function returns a JSON list of all stations"""
    print('Server request for list of stations...')

    # Retrieve list of stations
    session = Session(engine)
    station_data = session.query(station.station, station.name).all()
    session.close()

    # Create dictionary with station information
    station_list = []
    for stat, name in station_data:
        station_dict = {}
        station_dict["station"] = stat
        station_dict["name"] = name
        station_list.append(station_dict)
    
    # Return dictionary as a JSON list
    return jsonify(station_list)

@app.route("/api/v1.0/tobs")
def tobs():
    """Function returns a JSON list of the last 12 months of temperature observations for the most active stations"""
    print('Server request for temperature data for most active station...')

    # Retrieve the last 12 months of temperature data for the most active station
    session = Session(engine)
    end_date = last_date
    start_date = start_date = dt.datetime.strptime(end_date, '%Y-%m-%d').date() - rd(months=12)
    temp_data = session.query(measurement.date, measurement.tobs).\
        filter(measurement.date >= start_date).filter(measurement.date <= end_date).\
        filter(measurement.station == most_active_station).all()
    session.close()

    # Create a dictionary with temperature data
    temp_list = []
    for date, tobs in temp_data:
        temp_dict = {}
        temp_dict["date"] = date
        temp_dict["tobs"] = tobs
        temp_list.append(temp_dict)
    
    # Return dictionary as a JSON list
    return jsonify(temp_list)

# Using an optional variable in a route: https://stackoverflow.com/questions/14032066/can-flask-have-optional-url-parameters
@app.route("/api/v1.0/<start>", defaults={'end': None})
@app.route("/api/v1.0/<start>/<end>")
def temp_stats(start, end):
    """Return/display the minimum, average, and maximum temperature for the start/end date range"""
    print('Server request for temperature stats for a specified date range...')

    # Check if start date is a valid date
    try:
        start_date = str(dt.datetime.strptime(start, '%Y-%m-%d').date())
    except ValueError:
        return jsonify({'error': 'The start date is not valid. Be sure to use the format yyyy-mm-dd.'}), 404
    
    # Check if start date is before the first observation date
    if start_date < first_date:
        return jsonify({'error': f'The start date is before the first temperature observation on {first_date}.'}), 404
    
    # If no end date is entered, set end_date to last observation date
    if end == None:
        end_date = last_date
    else:
        # Verify the end date is a valid date
        try:
            end_date = str(dt.datetime.strptime(end, '%Y-%m-%d').date())
        except ValueError:
            return jsonify({'error': 'The end date is not valid. Be sure to use the format yyyy-mm-dd.'}), 404
        
        # Check if end date is after the last observation date
        if end_date > last_date:
            return jsonify({'error': f'The end date is after the last temperature observation on {last_date}.'}), 404

    # Check if start date is after the end date
    if start_date > end_date:
        return jsonify({'error': 'The start date is after the end date. Please enter a valid date range.'}), 404
    
    # Calculate the minimum, maximum and average temperature for observations within the date range.
    session = Session(engine)
    temp_stats = session.query(func.min(measurement.tobs), func.max(measurement.tobs), func.avg(measurement.tobs)).\
        filter(measurement.date >= start_date).filter(measurement.date <= end_date).all()
    session.close()

    # Create a dictionary with the temperature stats
    temp_list = [{'minimum temperature': temp_stats[0][0]}, 
                 {'maximum temperature': temp_stats[0][1]},
                 {'average temperature': temp_stats[0][2]}
                 ]
    
    # Return dictionary as a JSON list
    return jsonify(temp_list)

if __name__ == "__main__":
    app.run(debug=True)