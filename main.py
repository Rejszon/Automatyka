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
        {"name": "setTemerature", "min": 10, "max": 85, "default": 70, "label": 'Ustalona temperatura podgrzewania wody'},
        {"name": "outdoorTemperature", "min": 0, "max": 35, "default": 22, "label": 'Temperatura otoczenia'},
        {"name": "KP", "min": 0, "max": 10, "step":0.1, "default": 3, "label": 'Wzmocnienie Regulatora'},
        {"name": "Ti", "min": 0, "max": 260, "step":1, "default": 80, "label": 'Czas Zdwojenia'},
        {"name": "Td", "min": 0, "max": 100, "step":1, "default": 5, "label": 'Czas wyprzedzenia'},
        {"name": "Tp", "min": 0, "max": 1, "step":0.1, "default": 0.1, "label": 'Czas próbkowania'},
        {"name": "replenishMass", "min": 0, "max": 2, "default": 2, "label": 'Objętość dolewanej wody [l]'},
        {"name": "replenishTime", "min": 1, "max": 3000, "default": 1000, "label": 'Moment rozpoczęcia dolewania wody [s]'},
        {"name": "replenishTemperature", "min": 1, "max": 99, "default": 25, "label": 'Temperatura dolewanej wody'},
    ]

    if request.method == 'POST':
        slider_values = request.form
        processed_data = {key: float(value) for key, value in slider_values.items()}
        T, Q = simulate(3000, 
        processed_data['initalTemperature'], 
        2, 
        processed_data['setTemerature'], 
        4000,
        processed_data['outdoorTemperature'],
        processed_data['KP'],
        processed_data['Ti'],
        processed_data['Td'],
        processed_data.get('replenish',0),
        processed_data['replenishMass'],
        processed_data['replenishTime'],
        processed_data['replenishTemperature'],
        processed_data['Tp'])

        #T = list(map(int,T))
        T = [round(x,2) for x in T]
        Q = [round(x,2) for x in Q]

        #Stwórz wykresy
        time = list(range(int(3001)*10))
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
Rt = 0.05 #Magic number który mówi o wymianie ciepła z otoczniem

def simulate(simTime, initialTemp, currMass, setTemp, maxQ, outTemp, Kp, Ti, Td ,repl, replMass, replTime, replTemp, Tp):
    temp = [initialTemp]
    q = [0]
    initialE = setTemp - initialTemp
    integral = 0
    addingWater = False

    for i in range(1, 10*(int(simTime)+1)):
        #Obliczamy obecne e oraz temperature
        currTemp = temp[-1]
        currE = setTemp - currTemp
        integral += currE
        derivative = (currE - initialE)
        #Regulator PID wzór
        currQ = Kp *( currE + Tp/Ti * integral + Td/Tp * derivative)
        currQ = max(0,min(currQ, maxQ))

        #Obliczenie tempratury (T[k])
        C = currMass * Cp
        newTemp = currTemp + Tp*((currQ / C) - (currTemp - outTemp)/(C * Rt))
        
        if repl and i == replTime * (1/Tp):
            addingWater = True
        if addingWater:
            replMass -= 0.2 * Tp  #Przyjmujemy że dolanie litra zajmuje 5 sekund więc co sekunde zmieniamy mase o 0.20 
            currMass += 0.2 * Tp
            newTemp = (currMass - 0.2 * Tp) / currMass * newTemp + (0.2 * Tp / currMass) * replTemp
            C = currMass * Cp
            if replMass <= 0:
                addingWater = False
        
        temp.append(newTemp)
        q.append(currQ)
        initialE = currE
    return temp,q

@app.route('/clear')
def clear_session():
    session.pop('previous_plots', None)
    return 'Dane wyczyszczone. Wróć do: <a href="/">formularza</a>.'
