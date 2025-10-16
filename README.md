# Atlas Find Related Work Item - Azure DevOps AI Studio

A modern, AI-powered tool for analyzing and managing Azure DevOps work items with intelligent insights and semantic search capabilities.

## ✨ Features

- **🔍 Intelligent Work Item Analysis**: AI-powered analysis of work items using multiple LLM providers
- **🎯 Smart Team Selection**: Automatic team selection based on work item patterns
- **📊 Advanced Analytics**: Comprehensive insights and reporting
- **🔗 Semantic Search**: Find related work items using natural language
- **🎨 Modern UI**: Clean, responsive React-based interface
- **⚡ Real-time Processing**: Live analysis and updates
- **🔧 Multi-Provider Support**: Integration with Claude, GPT, Gemini, and more

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+
- Azure DevOps Personal Access Token
- (Optional) OpenArena account for AI analysis

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/PonrajMahalingamTR/atlas-find-related-work-item.git
   cd atlas-find-related-work-item
   ```

2. **Set up environment variables:**
   ```bash
   cp env.example .env
   # Edit .env with your actual credentials
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r modern_ui_backend/requirements.txt
   ```

4. **Install Node.js dependencies:**
   ```bash
   cd modern_ui
   npm install
   cd ..
   ```

5. **Configure your settings:**
   ```bash
   cp config/ado_settings.txt.example config/ado_settings.txt
   # Edit config/ado_settings.txt with your Azure DevOps details
   ```

### Running the Application

#### Development Mode (Recommended)
```bash
python main.py
```
This will start both the Python backend and React frontend automatically.

#### Manual Setup
```bash
# Terminal 1: Start Python backend
python modern_ui_backend/enhanced_app.py

# Terminal 2: Start React frontend
cd modern_ui
npm start
```

## 🔐 Security Setup

**⚠️ IMPORTANT**: Before using this application, you must configure your credentials securely. See [SECURITY_SETUP.md](SECURITY_SETUP.md) for detailed instructions.

### Quick Security Setup

1. **Create your environment file:**
   ```bash
   cp env.example .env
   ```

2. **Add your Azure DevOps credentials:**
   ```bash
   # Edit .env file
   AZURE_DEVOPS_PAT=your_personal_access_token
   AZURE_DEVOPS_ORG_URL=https://dev.azure.com/your-org
   AZURE_DEVOPS_PROJECT=your-project-name
   ```

3. **Configure application settings:**
   ```bash
   cp config/ado_settings.txt.example config/ado_settings.txt
   # Edit with your organization details
   ```

## 📖 Usage

### 1. Connect to Azure DevOps
- Enter your organization URL and Personal Access Token
- Select your project and team
- Click "Connect" to establish the connection

### 2. Analyze Work Items
- Choose your analysis parameters
- Select the AI model for analysis
- Run the analysis to get intelligent insights

### 3. Explore Results
- View work item summaries and insights
- Use semantic search to find related items
- Export results for further analysis

## 🛠️ Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_DEVOPS_PAT` | Personal Access Token | Yes |
| `AZURE_DEVOPS_ORG_URL` | Organization URL | Yes |
| `AZURE_DEVOPS_PROJECT` | Project Name | Yes |
| `OPENARENA_ESSO_TOKEN` | OpenArena token | Optional |
| `LOG_LEVEL` | Logging level | No |

### Configuration Files

- `config/ado_settings.txt` - Azure DevOps settings
- `modern_ui/config/ado_settings.txt` - UI-specific settings
- `.env` - Environment variables (not committed to Git)

## 🔧 Development

### Project Structure

```
atlas-find-related-work-item/
├── main.py                          # Main launcher
├── modern_ui/                       # React frontend
│   ├── src/
│   ├── public/
│   └── package.json
├── modern_ui_backend/               # Python backend
│   ├── enhanced_app.py
│   └── requirements.txt
├── src/                            # Core Python modules
│   ├── ado/                        # Azure DevOps integration
│   ├── openarena/                  # OpenArena integration
│   └── gui/                        # GUI components
├── config/                         # Configuration files
├── data/                          # Data storage (excluded from Git)
└── logs/                          # Log files (excluded from Git)
```

### Adding New Features

1. **Backend API**: Add routes in `modern_ui_backend/enhanced_app.py`
2. **Frontend Components**: Add React components in `modern_ui/src/components/`
3. **Core Logic**: Add modules in `src/` directory

### Testing

```bash
# Run Python tests
python -m pytest

# Run React tests
cd modern_ui
npm test
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Development Guidelines

- Follow Python PEP 8 style guide
- Use meaningful commit messages
- Add documentation for new features
- Ensure all tests pass
- Never commit sensitive data

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check this README and [SECURITY_SETUP.md](SECURITY_SETUP.md)
- **Issues**: Create an issue on GitHub
- **Security**: Report security issues privately

## 🔄 Changelog

### v1.0.0
- Initial release
- Azure DevOps integration
- AI-powered work item analysis
- Modern React UI
- Multi-provider AI support

## 🙏 Acknowledgments

- Azure DevOps team for the excellent API
- OpenArena for AI integration capabilities
- React and Python communities for amazing tools

---

**Made with ❤️ for the Azure DevOps community**
