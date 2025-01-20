from flask import Flask, render_template, request
import plotly.express as px
import pandas as pd

app = Flask(__name__)

@app.route("/", methods = ['GET', 'POST'])
def index():
    sliders = [
        {"name": "initalTemperature", "min": 1, "max": 99, "default": 25, "label": 'Temperatura początkowa wody'},
        {"name": "initialMass", "min": 1, "max": 10, "default": 4, "label": 'Masa początkowa wody'},
        {"name": "setTemerature", "min": 10, "max": 99, "default": 80, "label": 'Ustalona temperatura podgrzewania wody'},
        {"name": "simulationTime", "min": 60, "max": 6000, "default": 1000, "label": 'Czas symulacji wyrażony w sekundach'},
        {"name": "heater", "min": 1000, "max": 3000, "default": 2000, "label": 'Moc grzałki'},
        {"name": "outdoorTemperature", "min": 0, "max": 35, "default": 22, "label": 'Temperatura otoczenia'},
        {"name": "KP", "min": 0, "max": 1000, "default": 300, "label": 'Człon proporcjonalny P'},
        {"name": "KI", "min": 0, "max": 1000, "default": 500, "label": 'Człon całkujący I'},
        {"name": "KD", "min": 0, "max": 1000, "default": 50, "label": 'Człon różniczkujący D'},
        {"name": "replenishMass", "min": 0, "max": 9, "default": 50, "label": 'Masa dolanej wody'},
        {"name": "replenishTime", "min": 1, "max": 1000, "default": 50, "label": 'Czas dolania'},
        {"name": "replenishTemperature", "min": 1, "max": 99, "default": 50, "label": 'Temperatura dolanej wody'},
    ]

    if request.method == 'POST':
        slider_values = request.form
        processed_data = {key: int(value) for key, value in slider_values.items()}
        T, Q = simulate(processed_data['simulationTime'], 
        processed_data['initalTemperature'], 
        processed_data['initialMass'], 
        processed_data['setTemerature'], 
        processed_data['heater'],
        processed_data['outdoorTemperature'],
        processed_data['KP'],
        processed_data['KI'],
        processed_data['KD'],
        processed_data.get('replenish',0),
        processed_data['replenishMass'],
        processed_data['replenishTime'],
        processed_data['replenishTemperature'],)
        #Stwórz wykresy
        time = list(range(processed_data['simulationTime'] + 1))
        data = pd.DataFrame({
        'Czas [s]': time,
        'Temperatura [°C]': T,
        'Moc grzałki [W]': Q
        })

        # Wykres temperatury od czasu
        fig1 = px.line(data, x='Czas [s]', y='Temperatura [°C]', title='Zmiana temperatury w czasie')
        fig1_temp = fig1.to_html(full_html=False)

        # Wykres mocy grzałki od czasu
        fig2 = px.line(data, x='Czas [s]', y='Moc grzałki [W]', title='Moc grzałki w czasie')
        fig2_temp = fig2.to_html(full_html=False)

        return render_template('result.html', plot1=fig1_temp, plot2=fig2_temp)

    return render_template('index.html', sliders=sliders)

Cp = 4186 #ciepło właściwe płynu
dt = 1 #krok czasowy pewnie zostawimy 1 na sztywno albo dodamy opcje wyboru
Rt = 0.05 #Magic number który mówi o wymianie ciepła z otoczniem

def simulate(simTime, initialTemp, currMass, setTemp, maxQ, outTemp, Kp, Ki, Kd ,repl, replMass, replTime, replTemp):
    temp = [initialTemp]
    q = [0]
    initialE = setTemp - initialTemp
    integral = 0

    for i in range(1, simTime+ 1):
        #Obliczamy obecne e oraz temperature
        currTemp = temp[-1]
        currE = setTemp - currTemp
        integral += currE * dt
        derivative = (currE - initialE) / dt
        #Regulator PID wzór
        currQ = Kp * currE + Ki * integral + Kd * derivative
        currQ = max(0,min(currQ, maxQ))

        #Obliczenie tempratury (T[k])
        C = currMass * Cp
        newTemp = currTemp + dt*((currQ / C) - (currTemp - outTemp)/(C * Rt)) 
        
        if repl and i == replTime:
            currMass += replMass
            newTemp = (currMass - replMass) / currMass * newTemp + (replMass / currMass) * replTemp
            C = currMass * Cp

        temp.append(newTemp)
        q.append(currQ)
        initialE = currE
    return temp,q
