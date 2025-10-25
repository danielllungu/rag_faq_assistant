import { inject } from '@angular/core';
import { CanActivateFn, Router, UrlTree } from '@angular/router';
import { ApiService } from '../services/api.service';

export const apiKeyGuard: CanActivateFn = (): boolean | UrlTree => {
  const apiService = inject(ApiService);
  const router = inject(Router);

  return apiService.apiKey ? true : router.createUrlTree(['/']);
};
