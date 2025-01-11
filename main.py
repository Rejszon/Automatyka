from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    temps,q = simulate(200,20,0.5,80)
    return render_template('index.html',T = temps,Q=q)

#To jest do dobrania obecnie losowe wartości z neta
Kp = 1000
Ki = 1
Kd = 200


Rt = 0.05 #Magic number który mówi o wymianie ciepła z otoczniem
outTemp = 25 #Temperatura na zewnątrz
Cp = 4186 #ciepło właściwe płynu
maxQ = 2000 #Maksymalna moc grzałki
dt = 1 #krok czasowy pewnie zostawimy 1 na sztywno albo dodamy opcje wyboru

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
