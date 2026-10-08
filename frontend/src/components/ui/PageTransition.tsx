import type { ReactNode } from 'react';
import { motion, useReducedMotion } from 'framer-motion';

export interface PageTransitionProps {
  children: ReactNode;
}

export function PageTransition({ children }: PageTransitionProps) {
  const shouldReduceMotion = useReducedMotion();
  
  const variants = shouldReduceMotion 
    ? undefined
    : {
        initial: { opacity: 0, y: 20 },
        animate: { opacity: 1, y: 0 },
        exit: { opacity: 0, y: -20 },
      };
  
  return (
    <motion.div
      initial="initial"
      animate="animate"
      exit="exit"
      variants={variants}
      transition={{ duration: 0.2 }}
    >
      {children}
    </motion.div>
  );
}
