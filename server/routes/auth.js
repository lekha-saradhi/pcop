const router = require('express').Router();
const jwt = require('jsonwebtoken');
const config = require('../config');

const USERS = [
    { id: 1, username: 'analyst', password: 'analyst123', role: 'analyst', name: 'Analytics User' },
    { id: 2, username: 'manager', password: 'manager123', role: 'manager', name: 'Portfolio Manager' },
    { id: 3, username: 'admin', password: 'admin123', role: 'admin', name: 'System Administrator' }
];

router.post('/login', (req, res) => {
    const { username, password } = req.body;

    if (!username || !password) {
        return res.status(400).json({
            status: 'error',
            message: 'Username and password are required'
        });
    }

    const user = USERS.find(u => u.username === username && u.password === password);

    if (!user) {
        return res.status(401).json({
            status: 'error',
            message: 'Invalid username or password'
        });
    }

    const payload = {
        id: user.id,
        username: user.username,
        role: user.role,
        name: user.name
    };

    const token = jwt.sign(payload, config.jwtSecret, {
        expiresIn: config.jwtExpiresIn
    });

    res.json({
        status: 'ok',
        token,
        user: {
            username: user.username,
            role: user.role,
            name: user.name
        }
    });
});

router.get('/me', require('../middleware/auth').verifyToken, (req, res) => {
    const user = USERS.find(u => u.username === req.user.username);
    if (!user) {
        return res.status(404).json({
            status: 'error',
            message: 'User not found'
        });
    }

    res.json({
        status: 'ok',
        user: {
            username: user.username,
            role: user.role,
            name: user.name
        }
    });
});

module.exports = router;
