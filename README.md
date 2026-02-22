# POPMAP - Point Of Presence Mapping & Analysis Platform

A tactical mapping application with pathfinding, hostile zone avoidance, and real-time collaboration features.

## Features

### 🗺️ Interactive Mapping
- Leaflet-based map with offline tile support
- Draw markers, lines, polygons, and circles
- Color-coded features with hostile zone marking
- Real-time drawing synchronization

### 🛣️ Intelligent Pathfinding
- D* Lite algorithm for optimal path calculation
- Hostile zone avoidance
- Terrain-aware routing using DEM data
- Risk assessment (Low/Medium/High)
- Corridor-based path constraints

### 🔒 Security
- OTP-based authentication via email
- Session management
- Custom encryption for data backup
- SHA-256 hashing for credentials

### 📊 Risk Analysis
- Automatic path risk calculation
- Proximity-based threat assessment
- Visual alerts for dangerous routes
- Distance metrics to hostile zones

## Installation

### Prerequisites
- Python 3.8+
- Virtual environment (recommended)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd fixed
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
Create a `.env` file with:
```env
SECRET_KEY=your-secret-key-here
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

5. Run the application:
```bash
python flask_server.py
```

6. Access at: `http://localhost:80`

## Project Structure

```
/workspaces/fixed/
├── Core Application
│   ├── flask_server.py      Main Flask application
│   ├── dstar.py             D* Lite pathfinding algorithm
│   ├── hashing.py           Custom cryptographic functions
│   └── requirements.txt     Python dependencies
│
├── Data Files
│   ├── drawings.json        User drawings/markers
│   └── shared.json          Shared/synchronized drawings
│
├── Frontend
│   ├── templates/
│   │   ├── index.html       Main map interface
│   │   └── login.html       Authentication page
│   └── static/
│       ├── tiles/           Offline map tiles
│       ├── output_be.tif    DEM elevation data
│       ├── leaflet/         Leaflet library
│       └── leaflet-draw/    Drawing plugin
│
├── Tools & Utilities
│   └── tools/
│       ├── crypto_utils.py        Encryption library
│       ├── encrypt_drawings.py    Interactive encryption CLI
│       ├── quick_encrypt.py       Quick encryption script
│       └── quick_decrypt.py       Quick decryption script
│
└── Documentation
    └── docs/
        └── ENCRYPTION_README.md   Encryption guide
```

## Usage

### Login
1. Navigate to `/login`
2. Enter your callsign and email
3. Request OTP code
4. Enter received OTP to authenticate

### Drawing on Map
- Use the toolbar to create markers, lines, polygons, or circles
- Click features to edit properties:
  - Change color
  - Mark as hostile
  - Delete features

### Pathfinding
1. Enter start coordinates (lat,lon)
2. Enter goal coordinates (lat,lon)
3. Adjust corridor width (optional)
4. Click "Show Path"
5. Review risk assessment alert

### Risk Levels
- 🟢 **LOW**: Path maintains safe distance (>300m from hostile zones)
- 🟡 **MEDIUM**: Path passes near hostile zones (100-300m)
- 🔴 **HIGH**: Path very close to hostile zones (<100m)

## Data Encryption

Encrypt sensitive drawing data:

```bash
# Interactive mode
python tools/encrypt_drawings.py

# Quick encrypt
python tools/quick_encrypt.py "your_password"

# Quick decrypt
python tools/quick_decrypt.py "your_password" output.json
```

See [ENCRYPTION_README.md](docs/ENCRYPTION_README.md) for details.

## API Endpoints

### Authentication
- `POST /request_otp` - Request OTP code
- `POST /login_verify` - Verify OTP and login
- `GET /logout` - Logout user

### Data Management
- `POST /save_drawings` - Save drawings
- `GET /merge_drawings` - Get merged drawings

### Pathfinding
- `GET /compute_path` - Calculate path with parameters:
  - `start_lat`, `start_lon` - Starting coordinates
  - `goal_lat`, `goal_lon` - Destination coordinates
  - `corridor` - Search corridor width (meters)

### Map Configuration
- `GET /tile_bounds` - Get tile coverage bounds

## Development

### Running in Debug Mode
```bash
export FLASK_DEBUG=1
python flask_server.py
```

### Testing Encryption
```bash
python tools/test_encryption.py
```

### Cleaning Workspace
```bash
python cleanup.py
```

## Technologies

- **Backend**: Flask, Python 3
- **Frontend**: Leaflet.js, Leaflet.Draw
- **Pathfinding**: D* Lite algorithm
- **Encryption**: Custom SHA-256 + stream cipher
- **Authentication**: OTP via SMTP
- **Maps**: Offline tile storage

## Security Considerations

⚠️ **Important Notes:**
- Change default `SECRET_KEY` in production
- Use app-specific passwords for email
- Custom encryption is for demonstration - consider standard libraries for production
- Keep `.env` file secure and never commit to git

## Contributing

1. Create feature branch
2. Make changes
3. Test thoroughly
4. Submit pull request

## License

[Specify your license here]

## Support

For issues or questions, please contact [your-contact-info]

---

**POPMAP** - Tactical mapping for mission planning and situational awareness
