import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import seaborn as sns
from werkzeug.utils import secure_filename
import sqlite3
from contextlib import contextmanager

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
STATIC_CHARTS = 'static/charts'
DATABASE = 'finance.db'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_CHARTS, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max 16MB files

# Set matplotlib style for professional charts
plt.style.use('default')
sns.set_palette("husl")

# Database setup
@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense', 'investment')),
                source TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount >= 0),
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

# Initialize database on startup
init_db()

def calculate_totals():
    """Calculate financial totals from database"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get totals by type
        cursor.execute('''
            SELECT type, SUM(amount) as total 
            FROM transactions 
            GROUP BY type
        ''')
        
        totals = {'income': 0, 'expense': 0, 'investment': 0}
        for row in cursor.fetchall():
            totals[row['type']] = row['total']
        
        # Calculate net savings
        net_savings = totals['income'] - totals['expense']
        
        return {
            'total_income': totals['income'],
            'total_expense': totals['expense'],
            'total_investment': totals['investment'],
            'net_savings': net_savings
        }

def get_transactions(limit=None):
    """Get transactions from database"""
    with get_db() as conn:
        cursor = conn.cursor()
        query = 'SELECT * FROM transactions ORDER BY date DESC, created_at DESC'
        if limit:
            query += f' LIMIT {limit}'
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]

def generate_chart(chart_type):
    """Generate professional charts using matplotlib and seaborn"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT source, SUM(amount) as total 
            FROM transactions 
            WHERE type = ? 
            GROUP BY source 
            ORDER BY total DESC
        ''', (chart_type,))
        
        data = cursor.fetchall()
        
        if not data:
            return None
        
        # Create figure with modern styling
        fig, ax = plt.subplots(figsize=(10, 8))
        fig.patch.set_facecolor('white')
        
        sources = [row['source'] for row in data]
        amounts = [row['total'] for row in data]
        
        # Color schemes for different chart types
        color_schemes = {
            'income': sns.color_palette("Greens_r", len(sources)),
            'expense': sns.color_palette("Reds_r", len(sources)),
            'investment': sns.color_palette("Purples_r", len(sources))
        }
        
        colors = color_schemes.get(chart_type, sns.color_palette("viridis", len(sources)))
        
        # Create donut chart
        wedges, texts, autotexts = ax.pie(amounts, labels=sources, autopct='%1.1f%%', 
                                         startangle=90, colors=colors,
                                         wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2))
        
        # Style the chart
        ax.set_title(f'{chart_type.capitalize()} Breakdown', 
                    fontsize=16, fontweight='bold', pad=20)
        
        # Make percentage text more readable
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(10)
        
        # Add total in center
        total = sum(amounts)
        ax.text(0, 0, f'Total\n${total:,.2f}', 
               horizontalalignment='center', verticalalignment='center',
               fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        # Save chart
        chart_path = os.path.join(STATIC_CHARTS, f'{chart_type}_chart.png')
        plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return f'charts/{chart_type}_chart.png'

def generate_trend_chart():
    """Generate monthly trend chart"""
    with get_db() as conn:
        df = pd.read_sql_query('''
            SELECT date, type, amount
            FROM transactions
            ORDER BY date
        ''', conn)
        
        if df.empty:
            return None
            
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.to_period('M')
        
        # Group by month and type
        monthly_data = df.groupby(['month', 'type'])['amount'].sum().unstack(fill_value=0)
        
        if monthly_data.empty:
            return None
            
        # Create trend chart
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor('white')
        
        # Plot lines for each type
        colors = {'income': '#10b981', 'expense': '#ef4444', 'investment': '#8b5cf6'}
        for col in monthly_data.columns:
            if col in colors:
                ax.plot(monthly_data.index.astype(str), monthly_data[col], 
                       marker='o', linewidth=3, markersize=8, 
                       color=colors[col], label=col.capitalize())
        
        ax.set_title('Monthly Financial Trends', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Month', fontsize=12)
        ax.set_ylabel('Amount ($)', fontsize=12)
        ax.legend(fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Format y-axis as currency
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save chart
        chart_path = os.path.join(STATIC_CHARTS, 'trend_chart.png')
        plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return 'charts/trend_chart.png'

@app.route('/')
def home():
    """Main dashboard route"""
    totals = calculate_totals()
    recent_transactions = get_transactions(limit=10)
    
    # Generate charts
    charts = {}
    for chart_type in ['income', 'expense', 'investment']:
        charts[chart_type] = generate_chart(chart_type)
    
    # Generate trend chart
    charts['trend'] = generate_trend_chart()
    
    return render_template('dashboard.html', 
                         totals=totals,
                         charts=charts,
                         transactions=recent_transactions)

@app.route('/api/transactions', methods=['GET'])
def api_get_transactions():
    """API endpoint to get transactions"""
    transactions = get_transactions()
    return jsonify(transactions)

@app.route('/api/transactions', methods=['POST'])
def api_add_transaction():
    """API endpoint to add transaction"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['date', 'type', 'source', 'amount']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Validate transaction type
        if data['type'] not in ['income', 'expense', 'investment']:
            return jsonify({'error': 'Invalid transaction type'}), 400
        
        # Validate amount
        try:
            amount = float(data['amount'])
            if amount < 0:
                return jsonify({'error': 'Amount must be positive'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid amount'}), 400
        
        # Insert into database
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO transactions (date, type, source, amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                data['date'],
                data['type'],
                data['source'],
                amount,
                data.get('description', '')
            ))
            conn.commit()
            transaction_id = cursor.lastrowid
        
        return jsonify({'message': 'Transaction added successfully', 'id': transaction_id}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions/<int:transaction_id>', methods=['DELETE'])
def api_delete_transaction(transaction_id):
    """API endpoint to delete transaction"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
            
            if cursor.rowcount == 0:
                return jsonify({'error': 'Transaction not found'}), 404
                
            conn.commit()
        
        return jsonify({'message': 'Transaction deleted successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard-data')
def api_dashboard_data():
    """API endpoint to get dashboard data"""
    totals = calculate_totals()
    return jsonify(totals)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Legacy file upload endpoint for Excel files"""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('home'))

    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('home'))

    if file and file.filename.endswith(('.xlsx', '.xls')):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Validate columns
            required_cols = ['date', 'type', 'source', 'amount']
            if not all(col in df.columns for col in required_cols):
                flash('Invalid file format. Must include: date, type, source, amount', 'error')
                return redirect(url_for('home'))

            # Clean and validate data
            df = df.dropna(subset=required_cols)
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            df = df.dropna(subset=['amount'])
            df = df[df['amount'] >= 0]  # Only positive amounts
            
            # Validate transaction types
            valid_types = ['income', 'expense', 'investment']
            df = df[df['type'].isin(valid_types)]
            
            if df.empty:
                flash('No valid transactions found in file', 'error')
                return redirect(url_for('home'))

            # Insert into database
            with get_db() as conn:
                for _, row in df.iterrows():
                    conn.execute('''
                        INSERT INTO transactions (date, type, source, amount, description)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        row['date'],
                        row['type'],
                        row['source'],
                        row['amount'],
                        row.get('description', '')
                    ))
                conn.commit()

            flash(f'{len(df)} transactions uploaded successfully!', 'success')
            
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'error')
        
        # Clean up uploaded file
        os.remove(file_path)
    else:
        flash('Please upload an Excel file (.xlsx or .xls)', 'error')

    return redirect(url_for('home'))

@app.route('/analytics')
def analytics():
    """Analytics page with detailed insights"""
    with get_db() as conn:
        # Get monthly trends
        df = pd.read_sql_query('''
            SELECT date, type, amount, source
            FROM transactions
            ORDER BY date
        ''', conn)
        
        analytics_data = {}
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df['month'] = df['date'].dt.to_period('M')
            
            # Monthly summaries
            monthly_summary = df.groupby(['month', 'type'])['amount'].sum().unstack(fill_value=0)
            
            # Top sources
            top_income = df[df['type'] == 'income'].groupby('source')['amount'].sum().sort_values(ascending=False).head(5)
            top_expenses = df[df['type'] == 'expense'].groupby('source')['amount'].sum().sort_values(ascending=False).head(5)
            
            analytics_data = {
                'monthly_summary': monthly_summary.to_dict() if not monthly_summary.empty else {},
                'top_income': top_income.to_dict(),
                'top_expenses': top_expenses.to_dict(),
                'total_transactions': len(df),
                'avg_transaction': df['amount'].mean()
            }
    
    return render_template('analytics.html', data=analytics_data)

@app.route('/export')
def export_data():
    """Export transactions to Excel"""
    transactions = get_transactions()
    
    if not transactions:
        flash('No transactions to export', 'error')
        return redirect(url_for('home'))
    
    df = pd.DataFrame(transactions)
    export_path = os.path.join(UPLOAD_FOLDER, f'finance_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx')
    df.to_excel(export_path, index=False)
    
    flash(f'Data exported to {export_path}', 'success')
    return redirect(url_for('home'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error_code=404, error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_code=500, error_message="Internal server error"), 500

if __name__ == '__main__':
    # Ensure static directories exist
    os.makedirs('static/charts', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # Run in debug mode for development
    app.run(debug=True, host='0.0.0.0', port=5000)