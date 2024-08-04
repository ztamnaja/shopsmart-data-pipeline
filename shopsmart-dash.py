import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State
import psycopg2
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.units import inch
from dotenv import load_dotenv
import os

load_dotenv()

database = os.getenv('DESTINATION_DB_NAME')
user = os.getenv('DESTINATION_DB_USER')
password = os.getenv('DESTINATION_DB_PASSWORD')
host = 'localhost'
port = '5434'

# Database connection
conn = psycopg2.connect(
   database=database, user=user, password=password, host=host, port=port
)
cursor = conn.cursor()

# Function to execute SQL queries and return results as a DataFrame
def execute_query(query, start_date=None, end_date=None):
    if start_date and end_date:
        cursor.execute(query, (start_date, end_date))
    else:
        cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(cursor.fetchall(), columns=columns)
    csv_string = df.to_csv(index=False, encoding='utf-8')
    return df, csv_string

# SQL Queries
queries = {
    'top_products': """
    SELECT p.product_name, SUM(s.quantity) as total_sold
    FROM fact_sales s
    JOIN dim_products p ON s.product_id = p.product_id
    {where_clause}
    GROUP BY p.product_name
    ORDER BY total_sold DESC
    LIMIT 10
    """,
    'avg_order_value': """
    SELECT c.customer_id, AVG(s.price * s.quantity) as avg_order_value
    FROM fact_sales s
    JOIN dim_customers c ON s.customer_id = c.customer_id
    {where_clause}
    GROUP BY c.customer_id
    """,
    'revenue_by_category': """
    SELECT p.category, SUM(s.price * s.quantity) as total_revenue
    FROM fact_sales s
    JOIN dim_products p ON s.product_id = p.product_id
    {where_clause}
    GROUP BY p.category
    """,
    'daily_sales_quantity': """
    SELECT DATE(timestamp) as date, SUM(quantity) as total_quantity
    FROM fact_sales
    {where_clause}
    GROUP BY DATE(timestamp)
    ORDER BY date
    """
}

# Initialize the Dash app
app = Dash(__name__, suppress_callback_exceptions=True)

# App layout
app.layout = html.Div([
    html.H1("ShopSmart Dashboard", style={'text-align': 'center'}),
    
    html.Div([
        dcc.DatePickerRange(
            id='date-picker-range',
            start_date=None,
            end_date=None,
            display_format='YYYY-MM-DD'
        ),
        html.Button('Download Report', id='generate-pdf-button', n_clicks=0),
        html.Button('Download CSV', id='download-csv-button', n_clicks=0),
    ], style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'gap': '20px'}),
    dcc.Download(id="download-pdf"),
    dcc.Download(id="download-csv"),
    html.Div([
        dcc.Graph(id='daily-sales-quantity-graph'),
        dcc.Graph(id='top-products-graph'),
        dcc.Graph(id='avg-order-value-graph'),
        dcc.Graph(id='revenue-by-category-graph')
    ])
])

@app.callback(
    [Output('daily-sales-quantity-graph', 'figure'),
     Output('top-products-graph', 'figure'),
     Output('avg-order-value-graph', 'figure'),
     Output('revenue-by-category-graph', 'figure')],
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)

def update_graphs(start_date, end_date):
    if start_date and end_date:
        start_date = pd.to_datetime(start_date).strftime('%Y-%m-%d')
        end_date = pd.to_datetime(end_date).strftime('%Y-%m-%d')
        where_clause = "WHERE s.timestamp BETWEEN %s AND %s"
    else:
        where_clause = ""
        start_date = end_date = None

    results = {}
    for name, query in queries.items():
        formatted_query = query.format(where_clause=where_clause)
        results[name], _ = execute_query(formatted_query, start_date, end_date)

    daily_sales_quantity_fig = px.line(results['daily_sales_quantity'], x='date', y='total_quantity', 
                                       title='Daily Sales Quantity Trend')
    
    top_products_fig = px.bar(results['top_products'], x='product_name', y='total_sold', 
                              title='Top 10 Best-Selling Products')
    
    avg_order_value_fig = px.box(results['avg_order_value'], y='avg_order_value', 
                                 title='Average Order Value per Customer')
    
    revenue_by_category_fig = px.pie(results['revenue_by_category'], values='total_revenue', names='category', 
                                     title='Total Revenue per Product Category')

    return daily_sales_quantity_fig, top_products_fig, avg_order_value_fig, revenue_by_category_fig



# Function to create a PDF report
def create_pdf_report(figures, start_date, end_date):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    
    styles = getSampleStyleSheet()
    title = "ShopSmart Dashboard Report"
    if start_date and end_date:
        date_range = f"Date Range: {start_date} to {end_date}"
    else:
        date_range = "Date Range: All Time"
    
    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(date_range, styles['Normal']))
    story.append(Spacer(1, 12))
    
    for name, fig in figures.items():
        img_bytes = fig.to_image(format="png", scale=2)
        img = Image(io.BytesIO(img_bytes), width=6*inch, height=4*inch)
        # story.append(Paragraph(name, styles['Heading2']))
        story.append(img)
        story.append(Spacer(1, 12))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


@app.callback(
    Output("download-pdf", "data"),
    Input("generate-pdf-button", "n_clicks"),
    State('date-picker-range', 'start_date'),
    State('date-picker-range', 'end_date'),
    prevent_initial_call=True,
)
def generate_pdf(n_clicks, start_date, end_date):
    if n_clicks > 0:
        
        figures = {
            'Daily Sales Quantity Trend': update_graphs(start_date, end_date)[0],
            'Total Revenue per Product Category': update_graphs(start_date, end_date)[3],
            'Top 10 Best-Selling Products': update_graphs(start_date, end_date)[1],
            'Average Order Value per Customer': update_graphs(start_date, end_date)[2],
        }
        
        pdf_buffer = create_pdf_report(figures, start_date, end_date)
        
        return dcc.send_bytes(pdf_buffer.getvalue(), "dashboard_report.pdf")

@app.callback(
    Output("download-csv", "data"),
    Input("download-csv-button", "n_clicks"),
    State('date-picker-range', 'start_date'),
    State('date-picker-range', 'end_date'),
    prevent_initial_call=True,
)
def download_csv(n_clicks, start_date, end_date):
    if n_clicks > 0:
        if start_date and end_date:
            start_date = pd.to_datetime(start_date).strftime('%Y-%m-%d')
            end_date = pd.to_datetime(end_date).strftime('%Y-%m-%d')
            where_clause = "WHERE s.timestamp BETWEEN %s AND %s"
        else:
            where_clause = ""
            start_date = end_date = None

        all_data = {}
        for name, query in queries.items():
            formatted_query = query.format(where_clause=where_clause)
            _, csv_string = execute_query(formatted_query, start_date, end_date)
            all_data[name] = csv_string

        # Combine all CSV data into a single string
        combined_csv = "\n\n".join([f"{name}\n{csv}" for name, csv in all_data.items()])

        return dict(content=combined_csv, filename="dashboard_data.csv")

if __name__ == '__main__':
    app.run_server(debug=True)