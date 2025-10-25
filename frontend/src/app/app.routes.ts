import { Routes } from '@angular/router';
import { ApiKeyComponent } from './features/api-key/api-key.component';
import { ChatComponent } from './features/chat/chat.component';
import { apiKeyGuard } from './guards/api-key.guard';

export const routes: Routes = [
  {
    path: '',
    component: ApiKeyComponent
  },
  {
    path: 'chat',
    component: ChatComponent,
    canActivate: [apiKeyGuard]
  },
  {
    path: '**',
    redirectTo: ''
  }
];
