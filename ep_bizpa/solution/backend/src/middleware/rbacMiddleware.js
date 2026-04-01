/**
 * Role-Based Access Control Middleware
 */

const checkRole = (...allowedRoles) => {
  return (req, res, next) => {
    // Get user role from request (set by auth middleware)
    const userRole = req.user?.role || 'guest';

    if (allowedRoles.includes(userRole) || allowedRoles.includes('*')) {
      return next();
    }

    return res.status(403).json({
      error: 'Forbidden',
      message: `Role '${userRole}' is not authorized for this action`
    });
  };
};

const requireAuth = (req, res, next) => {
  if (!req.user) {
    return res.status(401).json({
      error: 'Unauthorized',
      message: 'Authentication required'
    });
  }
  next();
};

module.exports = {
  checkRole,
  requireAuth
};
