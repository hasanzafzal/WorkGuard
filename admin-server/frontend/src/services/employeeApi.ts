import { request } from "./api";
import type { Employee, EmployeeDetail } from "../types";

export const employeeApi = {
  async getEmployees(): Promise<Employee[]> {
    return request<Employee[]>("/api/v1/employees", { method: "GET" });
  },

  async getEmployeeById(employeeId: string): Promise<EmployeeDetail> {
    return request<EmployeeDetail>(`/api/v1/employees/${employeeId}`, { method: "GET" });
  },
};
