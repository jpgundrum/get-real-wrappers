import { createLogger, format, transports } from 'winston';

// Configure the logger to write to a file only
export const sdkLogger = createLogger({
    level: 'debug', // Set logging level
    format: format.combine(
        format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }), // Add timestamp
        format.printf(({ timestamp, level, message }) => {
            return `${timestamp} - ${level.toUpperCase()}: ${message}`; // Format log message
        })
    ),
    transports: [
        new transports.File({ filename: './logs/peaq_sdk.log', level: 'debug' }), // Log to file
    ],
});

// Configure the logger to write to a file only
export const serverLogger = createLogger({
    level: 'debug', // Set logging level
    format: format.combine(
        format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }), // Add timestamp
        format.printf(({ timestamp, level, message }) => {
            return `${timestamp} - ${level.toUpperCase()}: ${message}`; // Format log message
        })
    ),
    transports: [
        new transports.File({ filename: './logs/server_sdk.log', level: 'debug' }), // Log to file
    ],
});
