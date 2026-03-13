/**
 * useCountUp - Animated number counter hook.
 * Counts from 0 to the target value over a duration, returns plain string.
 */

import { useState, useEffect } from "react";

export function useCountUp(targetValue = 0, duration = 1) {
  const [displayValue, setDisplayValue] = useState("0");

  useEffect(() => {
    const startTime = Date.now();
    const controls = setInterval(() => {
      const elapsedTime = (Date.now() - startTime) / 1000;
      const progress = Math.min(elapsedTime / duration, 1);
      const currentValue = Math.floor(progress * targetValue);
      setDisplayValue(currentValue.toLocaleString("en-US"));

      if (progress === 1) {
        clearInterval(controls);
      }
    }, 16); // ~60fps

    return () => clearInterval(controls);
  }, [targetValue, duration]);

  return displayValue;
}

/**
 * useCountUpCurrency - Like useCountUp but formats as currency.
 */
export function useCountUpCurrency(targetValue = 0, duration = 1) {
  const [displayValue, setDisplayValue] = useState("$0");

  useEffect(() => {
    const startTime = Date.now();
    const controls = setInterval(() => {
      const elapsedTime = (Date.now() - startTime) / 1000;
      const progress = Math.min(elapsedTime / duration, 1);
      const currentValue = Math.floor(progress * targetValue);
      setDisplayValue(`$${currentValue.toLocaleString("en-US")}`);

      if (progress === 1) {
        clearInterval(controls);
      }
    }, 16); // ~60fps

    return () => clearInterval(controls);
  }, [targetValue, duration]);

  return displayValue;
}
