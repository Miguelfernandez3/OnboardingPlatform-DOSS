/**
 * User Entity
 * Representa un usuario en el sistema
 */
export interface UserData {
  id: string;
  email: string;
  role: string;
  isActive: boolean;
  lastLogin?: string;
  createdAt?: string;
  updatedAt?: string;
}

export class User {
  id: string;
  email: string;
  role: string;
  isActive: boolean;
  lastLogin?: string;
  createdAt?: string;
  updatedAt?: string;

  constructor({
    id,
    email,
    role = 'user',
    isActive = true,
    lastLogin,
    createdAt,
    updatedAt
  }: UserData) {
    this.id = id;
    this.email = email;
    this.role = role;
    this.isActive = isActive;
    this.lastLogin = lastLogin;
    this.createdAt = createdAt;
    this.updatedAt = updatedAt;
  }

  static fromJSON(json: UserData | any): User {
    return new User({
      id: json.id || '',
      email: json.email || '',
      role: json.role || 'user',
      isActive: json.isActive !== undefined ? json.isActive : (json.is_active !== undefined ? json.is_active : true),
      lastLogin: json.lastLogin || json.last_login,
      createdAt: json.createdAt || json.created_at,
      updatedAt: json.updatedAt || json.updated_at
    });
  }

  toJSON(): UserData {
    return {
      id: this.id,
      email: this.email,
      role: this.role,
      isActive: this.isActive,
      lastLogin: this.lastLogin,
      createdAt: this.createdAt,
      updatedAt: this.updatedAt
    };
  }

  get isAdmin(): boolean {
    return this.role === 'admin';
  }
}
