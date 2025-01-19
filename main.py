from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/", methods = ['GET', 'POST'])
def index():
    sliders = [
        {"name": "initalTemperature", "min": 1, "max": 99, "default": 25, "label": 'Temperatura początkowa wody'},
        {"name": "initialMass", "min": 1, "max": 10, "default": 4, "label": 'Masa początkowa wody'},
        {"name": "setTemerature", "min": 10, "max": 99, "default": 20, "label": 'Ustalona temperatura podgrzewania wody'},
        {"name": "simulationTime", "min": 60, "max": 1000, "default": 300, "label": 'Czas symulacji wyrażony w sekundach'},
        {"name": "heater", "min": 1000, "max": 3000, "default": 2000, "label": 'Moc grzałki'},
        {"name": "outdoorTemperature", "min": 0, "max": 35, "default": 22, "label": 'Temperatura otoczenia'},
        {"name": "KP", "min": 0, "max": 600, "default": 300, "label": 'Człon proporcjonalny P'},
        {"name": "KI", "min": 0, "max": 1000, "default": 500, "label": 'Człon całkujący I'},
        {"name": "KD", "min": 0, "max": 100, "default": 50, "label": 'Człon różniczkujący D'},
    ]

    if request.method == 'POST':
        slider_values = request.form
        processed_data = {key: value for key, value in slider_values.items()}
        return render_template('result.html', data=processed_data)

    return render_template('index.html', sliders=sliders)

#To jest do dobrania obecnie losowe wartości z neta
Kp = 1000
Ki = 1
Kd = 200

maxQ = 2000 #Maksymalna moc grzałki
outTemp = 25 #Temperatura na zewnątrz

Cp = 4186 #ciepło właściwe płynu
dt = 1 #krok czasowy pewnie zostawimy 1 na sztywno albo dodamy opcje wyboru
Rt = 0.05 #Magic number który mówi o wymianie ciepła z otoczniem

def simulate(simTime, initialTemp, currMass, setTemp):
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

        temp.append(newTemp)
        q.append(currQ)
        initialE = currE
    return temp,q
