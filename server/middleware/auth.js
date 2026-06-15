const jwt = require('jsonwebtoken');
const config = require('../config');

function verifyToken(req, res, next) {
    const authHeader = req.headers.authorization;
    // Also accept ?token= query param for SSE connections (EventSource can't set headers)
    const queryToken = req.query.token;

    let token;
    if (authHeader && authHeader.startsWith('Bearer ')) {
        token = authHeader.substring(7);
    } else if (queryToken) {
        token = queryToken;
    } else {
        return res.status(401).json({
            status: 'error',
            message: 'Authorization header missing or invalid'
        });
    }

    try {
        const decoded = jwt.verify(token, config.jwtSecret);
        req.user = decoded;
        next();
    } catch (error) {
        if (error.name === 'TokenExpiredError') {
            return res.status(401).json({
                status: 'error',
                message: 'Token has expired'
            });
        }
        return res.status(401).json({
            status: 'error',
            message: 'Invalid token'
        });
    }
}

function requireRole(...roles) {
    return (req, res, next) => {
        if (!req.user) {
            return res.status(401).json({
                status: 'error',
                message: 'Authentication required'
            });
        }

        if (!roles.includes(req.user.role)) {
            return res.status(403).json({
                status: 'error',
                message: `Access denied. Required role: ${roles.join(' or ')}`
            });
        }

        next();
    };
}

module.exports = {
    verifyToken,
    requireRole
};
