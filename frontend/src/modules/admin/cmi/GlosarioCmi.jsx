import React from 'react';
import GlosarioFlotante from '../../../components/shared/GlosarioFlotante';
import { GLOSARIO_CMI } from './glosarioTextos';

export default function GlosarioCmi({ tema }) {
  return <GlosarioFlotante contenido={GLOSARIO_CMI[tema]} />;
}
