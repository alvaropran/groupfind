export interface ApiResponse<T> {
  readonly success: boolean;
  readonly data: T | null;
  readonly error: { readonly code: string; readonly message: string } | null;
}

export interface PaginatedResponse<T> extends ApiResponse<T> {
  readonly meta: {
    readonly total: number;
    readonly page: number;
    readonly limit: number;
  } | null;
}
