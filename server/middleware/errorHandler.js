module.exports = function errorHandler(err, req, res, next) {
    console.error('[Error]', err.stack || err.message || err);

    const status = err.status || err.response?.status || 500;
    const message = err.message || 'Internal server error';

    res.status(status).json({
        status: 'error',
        message: message
    });
};
