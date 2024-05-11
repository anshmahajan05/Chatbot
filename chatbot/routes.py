from chatbot import app
from flask import render_template,flash, request
from chatbot.forms import chatbotform
from chatbot.__init__ import model,words,classes,intents
from bs4 import BeautifulSoup
import nltk

nltk.download('wordnet')
nltk.download('punkt')
nltk.download('stopwords')

import pickle
import json
import numpy as np
from keras.models import Sequential,load_model
import random
from datetime import datetime
import pytz
import requests
import os
import billboard
import time
from pygame import mixer
import COVID19Py
from pycricbuzz import Cricbuzz
from nltk.stem import WordNetLemmatizer
lemmatizer=WordNetLemmatizer()


#Predict
def clean_up(sentence):
    sentence_words=nltk.word_tokenize(sentence)
    sentence_words=[ lemmatizer.lemmatize(word.lower()) for word in sentence_words]
    return sentence_words

def create_bow(sentence,words):
    sentence_words=clean_up(sentence)
    bag=list(np.zeros(len(words)))

    for s in sentence_words:
        for i,w in enumerate(words):
            if w == s:
                bag[i] = 1
    return np.array(bag)

def predict_class(sentence,model):
    p=create_bow(sentence,words)
    res=model.predict(np.array([p]))[0]
    threshold=0.8
    results=[[i,r] for i,r in enumerate(res) if r>threshold]
    results.sort(key=lambda x: x[1],reverse=True)
    return_list=[]

    for result in results:
        return_list.append({'intent':classes[result[0]],'prob':str(result[1])})
    return return_list

def get_response(return_list,intents_json,text):

    if len(return_list)==0:
        tag='noanswer'
    else:
        tag=return_list[0]['intent']
    if tag=='datetime':
        x=''
        tz = pytz.timezone('Asia/Kolkata')
        dt=datetime.now(tz)
        x+=str(dt.strftime("%A"))+' '
        x+=str(dt.strftime("%d %B %Y"))+' '
        x+=str(dt.strftime("%H:%M:%S"))
        return x,'datetime'



    if tag=='weather':
        x=''
        api_key='987f44e8c16780be8c85e25a409ed07b'
        base_url = "http://api.openweathermap.org/data/2.5/weather?"
        # city_name = input("Enter city name : ")
        city_name = text.split(':')[1].strip()
        complete_url = base_url + "appid=" + api_key + "&q=" + city_name
        response = requests.get(complete_url)
        response=response.json()
        pres_temp=round(response['main']['temp']-273,2)
        feels_temp=round(response['main']['feels_like']-273,2)
        cond=response['weather'][0]['main']
        x+='Present temp.:'+str(pres_temp)+'C. Feels like:'+str(feels_temp)+'C. '+str(cond)
        print(x)
        return x,'weather'

    if tag=='news':
        main_url = " http://newsapi.org/v2/top-headlines?country=in&apiKey=bc88c2e1ddd440d1be2cb0788d027ae2"
        open_news_page = requests.get(main_url).json()
        article = open_news_page["articles"]
        results = []
        x="<ol style='margin-left: 20px;'>"
        for ar in article:
            results.append([ar["title"],ar["url"]])

        for i in range(10):
            x+="<li>"
            x+=f'<a href="{results[i][1]}">'+str(results[i][0])
            x+="</a>"
            x+="</li>"
        x+="</ol>"

        return x,'news'

    if tag=='cricket':
        urls = ["https://www.cricbuzz.com/cricket-match/live-scores", "https://www.cricbuzz.com/cricket-match/live-scores/recent-matches", "https://www.cricbuzz.com/cricket-match/live-scores/upcoming-matches"]
        x = "<ul style='margin-left: 20px;'>"
        for url in urls:
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                index = 0
                
                type = url.split('/')[-1]
                print("type: ->", type)
                if type == "live-scores":
                    type="Live Matches"
                elif type == 'recent-matches':
                    type='Recent Matches'
                elif type == 'upcoming-matches':
                    type='Upcoming Matches'
                x+=f"<li>{type}</li>"
                x += "<ol style='margin-left: 30px;'>"
                
                # Find the live match updates
                live_matches = soup.find_all('div', class_='cb-mtch-lst cb-col cb-col-100 cb-tms-itm')

                if not live_matches:
                    x+= "No matches found."
            
            for match in live_matches:
                srs = match.find('a', class_='text-hvr-underline text-bold').text.strip()
                mnum = match.find('span', class_='text-gray').text.strip()
                try:
                    status = match.find('div', class_='cb-text-complete').text.strip()
                except:
                    try:
                        status = match.find('div', class_='cb-text-live').text.strip()
                    except:
                        status = "Upcoming Match"

                x += f"<li> {srs} - {mnum} : {status} </li>"
            x+="</ol>"
            x+="</li>"
        else:
            print("Failed to fetch cricket updates")
        x+="</ul>"
        return x, 'cricket'

    if tag=='song':
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials
        chart=billboard.ChartData('hot-100')
        x="The top 10 songs at the moment are: <ol style='margin-left: 20px;'>"
        for i in range(10):
            song=chart[i]
            x+='<li>'+str(song.title)+'- '+str(song.artist) #+ "\t Listen: " + str(song.spotifyLink)
            client_id = '7262d1a4a55a46beb973fa784b78503f'
            client_secret = '9d3382e5e1ae483baaf676178143cc17'
            sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))
            results = sp.search(q=song, type='track')
            if results['tracks']['total'] > 0:
                track = results['tracks']['items'][0]
                spotify_link = track['external_urls']['spotify']
                x+=f"<br>Spotify Link: <a href='{spotify_link}' target='_blank'> Click here </a></li>"
            else:
                x+="<br>Song not found on Spotify.</li>"
        x+='</ol>'
        return x,'songs'

    if tag=='timer':
        mixer.init()
        x=text.split(':')[1].strip()
        time.sleep(float(x)*60)
        mixer.music.load('Handbell-ringing-sound-effect.mp3')
        mixer.music.play()
        x='Timer ringing...'
        return x,'timer'


    if tag=='covid19':
        # Define the base URL for the disease.sh API
        base_url = "https://disease.sh/v3/covid-19"
        try:
            country=text.split(':')[1].strip()
        except:
            country='world'
        x=''
        try:
            if country.lower()=='world':
                global_data = requests.get(f"{base_url}/all").json()
            else:
                global_data = requests.get(f"{base_url}/countries/{country.lower()}").json()
            x+=f'Stats for COVID19 for {country}: <br>Todays Confirmed Cases:'+str(global_data['todayCases'])+'<br>Todays Deaths:'+str(global_data['todayDeaths'])+'<br>Todays Recovered:'+str(global_data['todayRecovered'])+'<br>Active:'+str(global_data['active'])+'<br>Critical:'+str(global_data['critical'])
            return x,'covid19'
        except Exception as e:
            print("error: ", e)

    list_of_intents= intents_json['intents']
    for i in list_of_intents:
        if tag==i['tag'] :
            result= random.choice(i['responses'])
    return result,tag

def response(text):
    return_list=predict_class(text,model)
    response,_=get_response(return_list,intents,text)
    return response



@app.route('/', methods=['GET','POST'])
#@app.route('/home',methods=['GET','POST'])
def yo():
    return render_template('main.html')

@app.route('/chat', methods=['GET','POST'])
#@app.route('/home',methods=['GET','POST'])
def home():
    return render_template('index.html')

@app.route("/get", methods=['GET','POST'])
def chatbot():
    # try:
    #     userText = str(request.args.get('msg'))
    #     print(userText)
    #     resp=response(userText)
    # except Exception as e:
    #     error_message = "An error occurred: " + str(e)
    #     resp = error_message
    resp="hi"
    return resp
