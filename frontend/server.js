const express = require('express');
const path = require('path');
const cors = require('cors');
const fs = require('fs');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000/api';

// Enable CORS
app.use(cors());

// Middleware to inject environment variables into HTML
app.use((req, res, next) => {
  if (req.path === '/' || req.path === '/index.html') {
    fs.readFile(path.join(__dirname, 'public', 'index.html'), 'utf8', (err, data) => {
      if (err) {
        return next(err);
      }
      
      // Inject environment variables before the closing </head> tag
      const envScript = `<script>
        window._env_ = {
          BACKEND_URL: "${BACKEND_URL}"
        };
      </script>`;
      
      const modifiedHtml = data.replace('</head>', `${envScript}</head>`);
      res.send(modifiedHtml);
    });
  } else {
    next();
  }
});

// Serve static files
app.use(express.static(path.join(__dirname, 'public')));
app.use('/src', express.static(path.join(__dirname, 'src')));

// Serve index.html for all routes (except those handled above)
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Start server
app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
  console.log(`Backend API URL: ${BACKEND_URL}`);
}); 