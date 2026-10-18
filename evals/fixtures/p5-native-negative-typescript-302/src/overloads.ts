export function wrap(value: string): {value: string};
export function wrap<T>(value: T): {value: T};
export function wrap<T>(value: T) { return {value}; }

export function first<T>(items: T[]): T | undefined;
export function first<T>(items: readonly T[]): T | undefined;
export function first<T>(items: readonly T[]) { return items[0]; }
