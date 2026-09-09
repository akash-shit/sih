import React, { useEffect, useState } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';

interface AnimatedCounterProps {
  value: number;
  duration?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  className?: string;
}

export const AnimatedCounter: React.FC<AnimatedCounterProps> = ({
  value,
  decimals = 0,
  prefix = '',
  suffix = '',
  className = '',
}) => {
  const spring = useSpring(0, {
    mass: 0.8,
    stiffness: 75,
    damping: 15,
  });

  const display = useTransform(spring, (current) => {
    const formatted = current.toLocaleString('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
    return `${prefix}${formatted}${suffix}`;
  });

  const [renderedValue, setRenderedValue] = useState(`${prefix}0${suffix}`);

  useEffect(() => {
    spring.set(value);
    const unsubscribe = display.on('change', (latest) => {
      setRenderedValue(latest);
    });
    return () => unsubscribe();
  }, [spring, display, value, prefix, suffix]);

  return (
    <motion.span className={className}>
      {renderedValue}
    </motion.span>
  );
};
