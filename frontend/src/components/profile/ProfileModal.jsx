import React, { useState } from 'react';
import { X, KeyRound, ShieldCheck, User, Check, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { authApi } from '../../api/authApi';
import { useNotifications } from '../../context/NotificationContext';
import { NOTIFICATION_CATEGORIES, NOTIFICATION_SEVERITIES } from '../../constants/systemConstants';

export default function ProfileModal({ isOpen, onClose }) {
  const { user } = useAuth();
  const { notify } = useNotifications();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  if (!isOpen) return null;

  const displayName = user?.name || user?.username || 'Usuario Institucional';
  const displayEmail = user?.email || (user?.username ? `${user.username}@giragroup.bo` : 'usuario@giragroup.bo');
  const displayRole = user?.role || 'ROL ACTIVO';
  const avatarInitials = (user?.name || user?.username || 'US')
    .split(' ')
    .map((p) => p[0])
    .join('')
    .substring(0, 2)
    .toUpperCase();

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!currentPassword) {
      setError('Debe ingresar su contraseña actual.');
      return;
    }
    if (newPassword.length < 6) {
      setError('La nueva contraseña debe tener al menos 6 caracteres.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('La confirmación no coincide con la nueva contraseña.');
      return;
    }

    setLoading(true);
    try {
      await authApi.changePassword(currentPassword, newPassword, confirmPassword);
      setSuccess('¡Contraseña actualizada exitosamente!');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');

      notify({
        title: 'Seguridad de la Cuenta',
        message: 'Su contraseña ha sido modificada correctamente.',
        category: NOTIFICATION_CATEGORIES.SEGURIDAD,
        severity: NOTIFICATION_SEVERITIES.INFO
      });

      setTimeout(() => {
        setSuccess('');
        onClose();
      }, 1500);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Error al cambiar la contraseña. Verifique su clave actual.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="modal-backdrop"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(23, 25, 28, 0.5)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 2000,
        padding: '20px',
      }}
    >
      <div
        className="modal-panel floating-artifact"
        style={{
          padding: '32px',
          borderRadius: 'var(--radius-cards)',
          width: '100%',
          maxWidth: '520px',
          border: '1px solid var(--color-border)',
          backgroundColor: 'var(--color-paper-white)',
          boxShadow: 'var(--shadow-modal)',
          position: 'relative',
          animation: 'modalPop 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <div>
            <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--color-slate-gray)', fontWeight: 600 }}>
              GIRA Group · Control de Identidad
            </span>
            <h3 className="serif-heading" style={{ fontSize: '24px', margin: '4px 0 0 0', color: 'var(--color-ink-black)' }}>
              Perfil de Usuario &amp; Credenciales
            </h3>
          </div>
          <button
            onClick={onClose}
            type="button"
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-slate-gray)', padding: '6px' }}
            title="Cerrar ventana"
          >
            <X size={20} />
          </button>
        </div>

        {/* User Card */}
        <div
          className="card-mist"
          style={{
            padding: '18px 20px',
            borderRadius: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            marginBottom: '24px',
            border: '1px solid var(--color-border)',
          }}
        >
          <div
            style={{
              width: '52px',
              height: '52px',
              borderRadius: '50%',
              backgroundColor: 'var(--color-ink-black)',
              color: 'var(--color-paper-white)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '18px',
              fontWeight: 700,
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
              flexShrink: 0,
            }}
          >
            {avatarInitials}
          </div>
          <div style={{ overflow: 'hidden', flex: 1 }}>
            <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-ink-black)', marginBottom: '2px' }}>
              {displayName}
            </div>
            <div style={{ fontSize: '13px', color: 'var(--color-slate-gray)', marginBottom: '6px' }}>
              {displayEmail}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span
                style={{
                  fontSize: '10.5px',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: '9999px',
                  backgroundColor: 'rgba(217, 155, 38, 0.15)',
                  color: 'var(--color-gira-gold)',
                  letterSpacing: '0.4px',
                }}
              >
                {displayRole}
              </span>
              <span
                style={{
                  fontSize: '11px',
                  color: 'var(--color-alert-green)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontWeight: 500,
                }}
              >
                <ShieldCheck size={13} /> 2FA Criptográfico Activo
              </span>
            </div>
          </div>
        </div>

        {/* Change Password Form */}
        <form onSubmit={handlePasswordSubmit}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <KeyRound size={16} color="var(--color-gira-gold)" />
            <h4 style={{ fontSize: '14px', fontWeight: 600, margin: 0, color: 'var(--color-ink-black)' }}>
              Actualización de Contraseña de Acceso
            </h4>
          </div>

          {error && (
            <div
              style={{
                backgroundColor: 'rgba(217, 56, 58, 0.1)',
                border: '1px solid rgba(217, 56, 58, 0.3)',
                color: 'var(--color-alert-red)',
                padding: '10px 14px',
                borderRadius: '12px',
                fontSize: '12.5px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '16px',
              }}
            >
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div
              style={{
                backgroundColor: 'rgba(27, 135, 84, 0.1)',
                border: '1px solid rgba(27, 135, 84, 0.3)',
                color: 'var(--color-alert-green)',
                padding: '10px 14px',
                borderRadius: '12px',
                fontSize: '12.5px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '16px',
              }}
            >
              <Check size={16} />
              <span>{success}</span>
            </div>
          )}

          {/* Current Password */}
          <div style={{ marginBottom: '14px' }}>
            <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 500, color: 'var(--color-slate-gray)', marginBottom: '6px' }}>
              Contraseña Actual
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type={showCurrent ? 'text' : 'password'}
                className="form-input"
                placeholder="Ingrese su contraseña actual"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                style={{ width: '100%', paddingRight: '40px' }}
                required
              />
              <button
                type="button"
                onClick={() => setShowCurrent(!showCurrent)}
                style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--color-slate-gray)', cursor: 'pointer' }}
              >
                {showCurrent ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* New Password */}
          <div style={{ marginBottom: '14px' }}>
            <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 500, color: 'var(--color-slate-gray)', marginBottom: '6px' }}>
              Nueva Contraseña (mínimo 6 caracteres)
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type={showNew ? 'text' : 'password'}
                className="form-input"
                placeholder="Defina su nueva contraseña"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                style={{ width: '100%', paddingRight: '40px' }}
                required
              />
              <button
                type="button"
                onClick={() => setShowNew(!showNew)}
                style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--color-slate-gray)', cursor: 'pointer' }}
              >
                {showNew ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* Confirm Password */}
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 500, color: 'var(--color-slate-gray)', marginBottom: '6px' }}>
              Confirmar Nueva Contraseña
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type={showConfirm ? 'text' : 'password'}
                className="form-input"
                placeholder="Reingrese la nueva contraseña"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                style={{ width: '100%', paddingRight: '40px' }}
                required
              />
              <button
                type="button"
                onClick={() => setShowConfirm(!showConfirm)}
                style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--color-slate-gray)', cursor: 'pointer' }}
              >
                {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* Form Actions */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button
              type="button"
              className="btn-pill-ghost"
              onClick={onClose}
              disabled={loading}
              style={{ padding: '9px 20px', fontSize: '13px' }}
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="btn-pill-dark"
              disabled={loading}
              style={{
                padding: '9px 24px',
                fontSize: '13px',
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading ? 'Guardando...' : 'Actualizar Contraseña'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
