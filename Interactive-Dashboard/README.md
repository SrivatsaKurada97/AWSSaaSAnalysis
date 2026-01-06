
```markdown
# 🎯 AWS SaaS Customer Analytics Dashboard

> **Interactive business intelligence dashboard built with Streamlit, SQL Server, and Claude AI to analyze customer lifecycle, revenue milestones, and engagement patterns.**

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![SQL Server](https://img.shields.io/badge/Microsoft_SQL_Server-CC2927?style=for-the-badge&logo=microsoft-sql-server&logoColor=white)](https://www.microsoft.com/sql-server)

## 📊 Project Overview

This project demonstrates end-to-end business intelligence development, from database design to interactive data visualization and AI-powered insights. Built as a portfolio project to showcase data analysis, SQL, Python, and modern BI tools.

### **Key Features:**
- 📈 **Real-time KPI tracking** - Customer metrics, revenue trends, engagement levels
- 🎯 **Customer lifecycle analysis** - Milestone tracking, time-to-value metrics
- 🤖 **AI-powered chat interface** - Natural language queries using Claude API
- 📊 **Interactive visualizations** - Plotly charts, Sankey diagrams, dynamic filters
- 🔄 **Automated data pipeline** - SQL → Python → Streamlit workflow

---

## 🖼️ Screenshots

### Overview Dashboard
![Overview Dashboard](screenshots/Overview.png)
*High-level KPIs showing total customers, revenue, CLV distribution, and engagement metrics*

### Users & Events Analysis
![Users & Events](screenshots/Users&Events.png)
*Detailed customer segmentation and event timeline analysis*

### Milestone Tracking
![Milestones](screenshots/Milestones.png)
*Revenue milestone progression and customer lifecycle stages*

### AI Chat Interface
![AI Chat](screenshots/AI_Chat.png)
*Natural language queries powered by Claude AI with context-aware responses*

---

## 🛠️ Tech Stack

### **Backend & Data:**
- **SQL Server** - Database management and complex queries
- **pyodbc** - Python-SQL Server connectivity
- **Pandas** - Data manipulation and analysis

### **Frontend & Visualization:**
- **Streamlit** - Interactive web application framework
- **Plotly** - Dynamic, responsive charts and graphs
- **Python 3.10+** - Core programming language

### **AI Integration:**
- **Anthropic Claude API** - Natural language processing and insights
- **Context-aware querying** - Dataset-specific responses

---

## 📁 Project Structure

```
aws-saas-analytics-dashboard/
│
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
├── .gitignore                  # Git ignore rules
│
├── tabs/                       # Dashboard tabs/pages
│   ├── overview.py            # Overview KPIs and summary
│   ├── users_and_events.py   # Customer segmentation & events
│   ├── milestones.py          # Lifecycle & milestone tracking
│   └── ai_chat.py             # Claude AI chat interface
│
├── utils/                      # Utility modules
│   ├── data_loader.py         # Database connection & queries
│   └── ai_chat.py             # Claude API integration
│
├── sql/                        # SQL scripts
│   ├── create_tables.sql      # Database schema
│   ├── load_data.sql          # Data import scripts
│   └── queries.sql            # Sample queries
│
└── screenshots/                # Dashboard screenshots
    ├── overview.png
    ├── users_events.png
    ├── milestones.png
    └── ai_chat.png
```

---

## 🚀 Getting Started

### **Prerequisites**

- Python 3.10 or higher
- SQL Server (local or Azure)
- Claude API key (optional, for AI features)

### **Installation**

1. **Clone the repository**
   ```bash
   git clone https://github.com/SrivatsaKurada97/AWSSaaSAnalysis.git
   cd Interactive-Dashboard
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up database connection**
   
   Create a `.streamlit/secrets.toml` file:
   ```toml
   [database]
   server = "your-server.database.windows.net"
   database = "your-database-name"
   username = "your-username"
   password = "your-password"
   driver = "ODBC Driver 17 for SQL Server"
   ```

5. **Run the application**
   ```bash
   streamlit run app.py
   ```

6. **Access the dashboard**
   - Open browser to `http://localhost:8501`

---

## 💡 Key Features Explained

### **1. Customer Lifecycle Tracking**

The dashboard calculates revenue milestones dynamically from event data:

```sql
-- Example: Calculate when customers reach $10K, $20K, $30K revenue
WITH cumulative_events AS (
    SELECT 
        customerID,
        event_timestamp,
        SUM(sales) OVER (
            PARTITION BY customerID 
            ORDER BY event_timestamp
        ) as cumulative_revenue
    FROM aws_events
)
SELECT 
    customerID,
    MIN(CASE WHEN cumulative_revenue >= 10000 THEN event_timestamp END) as first_10k_date,
    MIN(CASE WHEN cumulative_revenue >= 20000 THEN event_timestamp END) as first_20k_date,
    MIN(CASE WHEN cumulative_revenue >= 30000 THEN event_timestamp END) as first_30k_date
FROM cumulative_events
GROUP BY customerID;
```

**Business Impact:** Identify fast-growing customers and optimize onboarding to reduce time-to-value.

---

### **2. AI-Powered Analytics**

Integration with Claude AI enables natural language queries:

```python
# Users can ask questions like:
# - "Show me top 10 customers by revenue"
# - "Which customers are at risk of churning?"
# - "What's the average time to reach $20K?"

# Claude responds with:
# - Specific data from the dataset
# - Business insights and recommendations
# - Formatted tables and metrics
```

**Technical Achievement:** Built custom context-aware prompt engineering to ensure accurate, data-specific responses.

---

### **3. Advanced Segmentation**

Multi-dimensional customer segmentation combining:
- **CLV Tier** (Platinum, Gold, Silver, Bronze)
- **Engagement Level** (High, Medium, Low, Strategic VIP)
- **Lifecycle Stage** (Developing, Growing, Mature, At-Risk)

**Visualization:** Sankey diagram showing customer flow through segments.

---

## 📊 Sample Insights Generated

**Customer Health:**
- 40.4% of customers have reached the $30K+ revenue milestone
- Platinum tier: 19.2% of customers contribute 46.0% of revenue
- Customers typically take 67 days to reach $10K milestone

**Engagement Patterns:**
- Strategic VIP customers have 2.3x higher revenue than average
- High engagement correlates with 85% faster revenue growth
- 15% of customers show at-risk patterns (low engagement + tenure >365 days)

**Growth Opportunities:**
- 12 Gold tier customers within 10% of Platinum threshold (upsell targets)
- 8 customers with high engagement but low product adoption (cross-sell opportunities)

---

## 🎯 Skills Demonstrated

### **Technical Skills:**
- ✅ **SQL Development** - Complex queries, window functions, CTEs, performance optimization
- ✅ **Python Programming** - Data manipulation with Pandas, API integration, error handling
- ✅ **Data Visualization** - Plotly charts, Streamlit dashboards, UX design
- ✅ **Database Design** - Normalized schema, relationships, indexing strategy
- ✅ **AI Integration** - Claude API, prompt engineering, context management

### **Business Skills:**
- ✅ **KPI Definition** - Identified key metrics for SaaS business health
- ✅ **Customer Lifecycle Analysis** - Milestone tracking, cohort analysis
- ✅ **Insight Generation** - Translating data into actionable recommendations
- ✅ **Stakeholder Communication** - Dashboard design for executive audiences

---

## 🔄 Data Pipeline

```
Raw Data (SQL Server)
    ↓
Python Data Loader (pyodbc)
    ↓
Data Transformation (Pandas)
    ↓
Streamlit Caching (@st.cache_data)
    ↓
Interactive Dashboard (Streamlit + Plotly)
    ↓
AI Enhancement (Claude API)
```

**Performance:** Cached data updates on refresh, queries optimized with CTEs and proper indexing.

---

## 🧪 Testing & Validation

- ✅ Verified data accuracy against source SQL queries
- ✅ Tested edge cases (empty data, single customer, missing values)
- ✅ Validated AI responses for accuracy and relevance
- ✅ Cross-browser compatibility testing
- ✅ Performance testing with 10K+ event records

---

## 📈 Future Enhancements

- [ ] **Predictive Analytics** - ML models for churn prediction
- [ ] **Real-time Streaming** - Live event ingestion and updates
- [ ] **Export Functionality** - Download reports as PDF/Excel
- [ ] **Multi-tenancy** - Support for multiple client databases
- [ ] **Advanced Filters** - Date ranges, custom segments
- [ ] **Email Alerts** - Automated notifications for key metrics

---

## 📚 Learning Resources

**Technologies Used:**
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Plotly Python Guide](https://plotly.com/python/)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [SQL Server Window Functions](https://learn.microsoft.com/en-us/sql/t-sql/queries/select-over-clause-transact-sql)

---

## 👤 About the Developer

**Srivatsa Kurada**  
Data Analyst | MS Information Science & Technology

- 4+ years experience in BI and data analytics
- Microsoft Certified: Power BI Data Analyst, Fabric Analytics Engineer, Azure AI Engineer
- Specialization: Customer analytics, SaaS metrics, Data Visualization, Prompt Engineering

**Connect:**
- 💼 [LinkedIn](https://www.linkedin.com/in/srivatsa-kurada)
- 📧 [Email](mailto:srivatsakurada@gmail.com)
- 📝 [Portfolio Article](https://YOUR_SUBSTACK_LINK)

---

## 📄 License

This project is available for portfolio and educational purposes.

---

## 🙏 Acknowledgments

- Dataset structure inspired by AWS SaaS customer data models
- AI chat functionality powered by Anthropic's Claude API
- Dashboard design principles from modern BI best practices

---

## 📞 Contact

**Questions or feedback?** Feel free to reach out!

- Open an issue on GitHub
- Connect on LinkedIn
- Email: srivatsakurada@gmail.com

---

**⭐ If you found this project helpful, please consider giving it a star!**
```