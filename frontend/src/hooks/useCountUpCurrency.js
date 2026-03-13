import { useEffect, useState } from "react";

/**
 * Hook to animate counting up to a currency value
 * Usage: const displayValue = useCountUpCurrency(1234.56, 1000);
 */
export function useCountUpCurrency(targetValue, duration = 1000) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    let startTime = null;
    let animationId = null;

    const animate = (currentTime) => {
      if (!startTime) startTime = currentTime;
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);

      setDisplayValue(Math.floor(targetValue * progress * 100) / 100);

      if (progress < 1) {
        animationId = requestAnimationFrame(animate);
      } else {
        setDisplayValue(targetValue);
      }
    };

    animationId = requestAnimationFrame(animate);

    return () => {
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
    };
  }, [targetValue, duration]);

  return displayValue;
}
