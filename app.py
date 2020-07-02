import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import dash
import dash_core_components as dcc
import dash_html_components as html
import os
# import ssl


# import case data and select texas
data = pd.read_csv('https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv')
texas = data[data['state']=='Texas']
pop = pd.read_csv('TxPop_Indexed.csv')
#import texas county geojson and make geodataframe for points
f = open('simp_tx_county.geojson')
p = pd.read_csv('points.csv')
tx_json = json.load(f)
#join cases data with case data
tx_geo = texas.merge(p, left_on='fips', right_on='GEOID')
tx_geo['county'] = tx_geo['county'] + ' County'
mer = tx_geo.merge(pop, left_on='county', right_on='CTYNAME')
tx_geo['2019 Population'] = mer['2019']
tx_geo['case_per10k'] = (tx_geo['cases']/tx_geo['2019 Population']) * 10000
# make new data frame for choropleth map
tx_case_geo = tx_geo[['county','fips','cases','deaths','date', 'case_per10k', '2019 Population','lat','lon']]


cases_over_time = texas[['date','county','cases']]
cases_over_time['roll'] = cases_over_time.groupby('county')['cases'].transform(lambda x: x.rolling(7).mean())
all_tx = pd.DataFrame()
all_tx['cases'] = texas.groupby(['date'])['cases'].sum()
all_tx['county'] = 'Texas'
all_tx['roll'] = all_tx['cases'].rolling(7).mean()
all_tx = all_tx.reset_index()
time_cases=all_tx.append(cases_over_time)
counties = time_cases['county'].sort_values().unique()

date = pd.DataFrame(tx_case_geo['date'].sort_values().unique())
date['num']=date.index
tx_case_geo = tx_case_geo.merge(date, left_on='date', right_on=0)

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
colors = {
    'background': 'snow',
    'text': 'black'
}
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title='Texas Covid Tracking'
server = app.server
app.layout = html.Div(style={'backgroundColor': colors['background']}, children=[
        html.H1(
            children='Texas Covid-19 Dashboard',
            style={
                'textAlign': 'center',
                'color': colors['text']
            }
        ),
        dcc.Markdown('''
            ### App Info

            Use the selection box below to choose a county. You can either select from the dropdown menu, or simply begin typing the name of a county in Texas and the available choices will update based on what is typed into the box. 

            The maps below show the spread of Covid-19 across Texas day to day. Use the slider to select a date to examine historical patterns in the spread of Covid-19 across Texas. You can also click on the slider button and then 
            use the left and right arrow keys to scrub through the timeline.

            Case data is sourced from [The New York Times GitHub page] (https://github.com/nytimes/covid-19-data). 

            ''',style={
            'textAlign': 'left',
            'color': colors['text'],
            'padding':5}),

        dcc.Dropdown(id='dd',
            options=[{'value':c, 'label':c,}for c in counties],
            value='Texas',
            style={"width":'30%'}),
        
        dcc.Graph(id = 'case_time',style={'padding': '20px'}),

        html.Div(dcc.Slider(id='slider',
            min= tx_case_geo['num'].min(),
            max = tx_case_geo['num'].max(),
            value= tx_case_geo['num'].max(),
            step=1, 
            marks ={
                18:'2020-03-01',
                49:'2020-04-01',
                79:'2020-05-01',
                110:'2020-06-01',
                140:'2020-07-01'
            },
            ),
            style={'width':'40%','margin':'auto'}),
        
        html.Div(style={'backgroundColor': colors['background']},children=[
        dcc.Graph(id = 'cnty_10k',style={'float':'left','width':'46%','padding':'20px'}),
        
        dcc.Graph(id = 'deaths', style={'float':'right','width':'46%','padding':'20px'})
        ])
])

@app.callback(dash.dependencies.Output('case_time','figure'),
    [dash.dependencies.Input('dd', 'value')])

def update_fig(value):
    selected_county = time_cases[time_cases['county'] == value]
    case_time = go.Figure(go.Bar(x = selected_county['date'], y = selected_county['cases'], name= 'Cases'))
    case_time.add_trace(go.Scatter(x = selected_county['date'], y = selected_county['roll'], name = '7 day Moving Average'))
    case_time.update_layout(hovermode='x unified',
                 paper_bgcolor = 'antiquewhite',
                 plot_bgcolor = 'lightgrey', 
                 height= 550,
                 margin={'l':25, 'r':25, 't':45, 'b':15},
                 title=value + ' - Current Number of Cases: ' + str(selected_county['cases'].tail(1).values).strip('[]')
                 )
    return case_time

@app.callback(dash.dependencies.Output('cnty_10k','figure'),
    [dash.dependencies.Input('slider', 'value')])
def update_map(value):
    selected_date = tx_case_geo.loc[tx_case_geo['num']==value]
    title = selected_date.date.unique()
    county = go.Figure(go.Choroplethmapbox(geojson=tx_json, locations=selected_date.fips, z=selected_date.case_per10k,
                                        colorscale="Sunsetdark", zmin=0, zmax=50,featureidkey='properties.GEOID',
                                        marker_opacity=0.8, marker_line_width=0.6,
                                        customdata=selected_date[['county','2019 Population','cases']],
                                        hovertemplate ='<b>County: %{customdata[0]}</b><br>Cases per 10,000: %{z}<br>2019 Population: %{customdata[1]:,3f}<br># of Cases: %{customdata[2]:,3f}'))
    county.update_layout(mapbox_style="carto-positron",
                    mapbox_zoom=5, mapbox_center = {"lat": 31.19282, "lon":-99.51260})
    county.update_layout(paper_bgcolor = 'antiquewhite',margin={'l':25, 'r':25, 't':45, 'b':15}, height=650, title ='Number of Cases per 10,000 by County on ' +str(title).strip('[]\''))
    return county

@app.callback(dash.dependencies.Output('deaths','figure'),
    [dash.dependencies.Input('slider', 'value')])
def death_map(value):
    sel_date = tx_case_geo.loc[tx_case_geo['num']==value]
    d_map = go.Figure(go.Scattermapbox(
        lat=sel_date.lat,
        lon=sel_date.lon,
        mode='markers',
        customdata=sel_date[['county','2019 Population','deaths']],
        hovertemplate ='<b>County: %{customdata[0]}</b><br>2019 Population: %{customdata[1]:,3f}<br># of Deaths: %{customdata[2]:,3f}',
        marker=go.scattermapbox.Marker(
            size=sel_date.deaths/7,
            sizemin=3.5,
            color = sel_date.deaths,
            cmin=0,
            cmax=100,
            colorscale= "Sunsetdark",
            colorbar=dict(
                title="Deaths"
            ),
        ),
    ))
    d_map.update_layout(mapbox_style="carto-positron",
                    mapbox_zoom=5, mapbox_center = {"lat": 31.19282, "lon":-99.51260})
    d_map.update_layout(paper_bgcolor = 'antiquewhite',margin={'l':25, 'r':25, 't':45, 'b':15}, height=650, title ='Number of Deaths by County on '+ str(sel_date.date.unique()).strip('[]\''))
    return d_map

if __name__ == '__main__':
    app.run_server(debug=True)
