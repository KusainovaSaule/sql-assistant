import axios from "axios";

export class BackendClient {
  constructor(private baseUrl: string) {}

  async analyze(sql: string) {
    const resp = await axios.post(`${this.baseUrl}/analyze`, { sql });
    return resp.data;
  }
}
