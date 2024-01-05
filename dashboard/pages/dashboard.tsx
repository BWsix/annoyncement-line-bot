import {
  Button,
  Group,
  Mark,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import Head from "next/head";
import { useRouter } from "next/router";
import { useState } from "react";
import axios from "axios";

type ActivationResult =
  | {
      status: "success" | "error";
      data: string;
    }
  | {
      status: undefined;
      data: undefined;
    };

export default function HadhboardPage() {
  const router = useRouter();
  const { group_id, group_name } = router.query;

  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState("");

  const [disabled, setDisalbed] = useState(false);

  const handleSubmit = () => {
    setDisalbed(true);
    axios
      .post(process.env.NEXT_PUBLIC_ACTIVATION_API, {
        group_id,
        group_name,
        invite_code: code,
      })
      .then((res) => {
        if (res.status != 200) {
          setError("Unexpected error occured.");
          return;
        }

        const { status, data } = res.data as ActivationResult;
        if (status === "success") {
          setResult(data);
          return;
        } else if (status === "error") {
          setError(data);
          setDisalbed(false);
          return;
        }
      });
  };

  return (
    <>
      <Head>
        <title>Dashboard</title>
      </Head>

      <Group m={50} justify="center">
        <Stack>
          <Title order={2}>Activate Annoyncement Line Bot</Title>

          <Text>
            To receive annoyncements in <Mark>{group_name}</Mark>, enter your
            invite code below and press the Activate button.
          </Text>

          <TextInput
            label="Invite Code"
            description="Can be found in administrators' group."
            value={code}
            onChange={(e) => setCode(e.currentTarget.value)}
            disabled={disabled}
            error={error}
          />
          <Button disabled={disabled} onClick={() => handleSubmit()}>
            Activate
          </Button>

          <Text>{result}</Text>
        </Stack>
      </Group>
    </>
  );
}
