from flask import Flask, render_template, request, session
from flask_session import Session
import plotly.express as px
import pandas as pd

app = Flask(__name__)
app.secret_key = 'very_secret_key' #potrzebne do stworzenia sesji, w naszym przypadku bezpieczeństwo nie jest istotne
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

@app.route("/", methods = ['GET', 'POST'])
def index():
    sliders = [
        {"name": "initalTemperature", "min": 1, "max": 99, "default": 25, "label": 'Temperatura początkowa wody'},
        {"name": "initialMass", "min": 1, "max": 7, "default": 4, "label": 'Objętość wody [l]'},
        {"name": "setTemerature", "min": 10, "max": 85, "default": 70, "label": 'Ustalona temperatura podgrzewania wody'},
        {"name": "outdoorTemperature", "min": 0, "max": 35, "default": 22, "label": 'Temperatura otoczenia'},
        {"name": "KP", "min": 0, "max": 1000, "step":2, "default": 100, "label": 'Wzmocnienie Regulatora'},
        {"name": "KI", "min": 0, "max": 0.2, "step":0.001, "default": 0.04, "label": 'Czas Zdwojenia'},
        {"name": "KD", "min": 0, "max": 50, "step":1, "default": 20, "label": 'Czas wyprzedzenia'},
        {"name": "replenishMass", "min": 0, "max": 3, "default": 2, "label": 'Objętość dolewanej wody [l]'},
        {"name": "replenishTime", "min": 1, "max": 5000, "default": 1000, "label": 'Moment rozpoczęcia dolewania wody [s]'},
        {"name": "replenishTemperature", "min": 1, "max": 99, "default": 25, "label": 'Temperatura dolewanej wody'},
    ]

    if request.method == 'POST':
        slider_values = request.form
        processed_data = {key: float(value) for key, value in slider_values.items()}
        T, Q = simulate(5000, 
        processed_data['initalTemperature'], 
        processed_data['initialMass'], 
        processed_data['setTemerature'], 
        2000,
        processed_data['outdoorTemperature'],
        processed_data['KP'],
        processed_data['KI'],
        processed_data['KD'],
        processed_data.get('replenish',0),
        processed_data['replenishMass'],
        processed_data['replenishTime'],
        processed_data['replenishTemperature'])

        #Stwórz wykresy
        time = list(range(int(5001)))
        data = pd.DataFrame({
        'Czas [s]': time,
        'Temperatura [°C]': T,
        'Moc grzałki [W]': Q
        })

        # Wykres temperatury od czasu
        fig1 = px.line(data, x='Czas [s]', y='Temperatura [°C]', title='Temperatura')
         # Wykres mocy grzałki od czasu
        fig2 = px.line(data, x='Czas [s]', y='Moc grzałki [W]', title='Ciepło grzałki')
        
        hovertemplateT = "Czas [s]: %{x}<br>Temperatura [°C]: %{y}<extra></extra>"
        hovertemplateQ = "Czas [s]: %{x}<br>Moc grzałki [W]: %{y}<extra></extra>"
        if 'previous_plots' in session:
            for idx, prev_data in enumerate(session['previous_plots'],start=1):
                prev_df = pd.DataFrame(prev_data)
                fig1.add_scatter(x=prev_df['Czas [s]'], y=prev_df['Temperatura [°C]'], mode='lines',name=f"Symulacja -{idx}", hovertemplate=hovertemplateT)
                fig2.add_scatter(x=prev_df['Czas [s]'], y=prev_df['Moc grzałki [W]'], mode='lines',name=f"Symulacja -{idx}", hovertemplate=hovertemplateQ)
        #Dodanie lini wartości zadanej
        fig1.add_shape(type="line",x0=min(time), x1=max(time),y0=processed_data['setTemerature'], y1=processed_data['setTemerature'],line=dict(color="red", width=2, dash="dash"))

        fig1_temp = fig1.to_html(full_html=False)
        fig2_temp = fig2.to_html(full_html=False)
       
        current_data = data.to_dict(orient='list')
        if 'previous_plots' not in session:
            session['previous_plots'] = []
        session['previous_plots'].insert(0,current_data)
        if len(session['previous_plots']) > 2:
            session['previous_plots'] = session['previous_plots'][:2]

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
    addingWater = False

    for i in range(1, int(simTime)+1):
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
            addingWater = True
        if addingWater:
            replMass -= 0.20 #Przyjmujemy że dolanie litra zajmuje 5 sekund więc co sekunde zmieniamy mase o 0.20 
            currMass += 0.20
            newTemp = (currMass - 0.20) / currMass * newTemp + (0.20 / currMass) * replTemp
            C = currMass * Cp
            if replMass <= 0:
                addingWater = False
        
        temp.append(round(newTemp,2))
        q.append(round(currQ))
        initialE = currE
    return temp,q

@app.route('/clear')
def clear_session():
    session.pop('previous_plots', None)
    return 'Dane wyczyszczone. Wróć do: <a href="/">formularza</a>.'
